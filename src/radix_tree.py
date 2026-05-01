from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AccessResult:
    hit_tokens: int
    inserted_tokens: int

    @property
    def full_hit(self) -> bool:
        return self.inserted_tokens == 0


@dataclass(slots=True, eq=False)
class TreeNode:
    key: tuple[int, ...]
    prefix: tuple[int, ...]
    parent: "TreeNode | None" = None
    created_at: int = -1
    last_access_index: int = -1
    access_count: int = 0
    priority: int | float = 0
    children: dict[int, "TreeNode"] = field(default_factory=dict)

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def is_leaf(self) -> bool:
        return not self.children

    @property
    def token_length(self) -> int:
        return len(self.key)

    @property
    def token(self) -> int | None:
        return None if not self.key else self.key[0]


class RadixTree:
    def __init__(self, token_budget: int, eviction_strategy) -> None:
        self.token_budget = token_budget
        self.eviction_strategy = eviction_strategy
        self.root = TreeNode(key=(), prefix=())
        self.cached_token_count = 0
        self.evictable_leaves: set[TreeNode] = set()

    def lookup(self, tokens: list[int], access_index: int | None = None) -> AccessResult:
        hit_tokens, _node = self._match_prefix(tokens, access_index=access_index)
        return AccessResult(hit_tokens=hit_tokens, inserted_tokens=len(tokens) - hit_tokens)

    def access(
        self,
        tokens: list[int],
        access_index: int,
        priority: int | float = 0,
    ) -> AccessResult:
        result = self.lookup(tokens, access_index=access_index)
        self.insert_suffix(
            tokens,
            start_index=result.hit_tokens,
            access_index=access_index,
            priority=priority,
        )
        self.evict_until_within_budget()
        return result

    def insert_suffix(
        self,
        tokens: list[int],
        start_index: int,
        access_index: int,
        priority: int | float = 0,
    ) -> int:
        terminal_node, path = self._locate_exact_node(tokens[:start_index])
        for node in path:
            node.priority = max(node.priority, priority)

        remainder = tuple(tokens[start_index:])
        if not remainder:
            return 0

        new_node = TreeNode(
            key=remainder,
            prefix=tuple(tokens),
            parent=terminal_node,
            created_at=access_index,
            last_access_index=access_index,
            access_count=1,
            priority=priority,
        )
        terminal_node.children[remainder[0]] = new_node
        self.cached_token_count += len(remainder)
        self._update_leaf_status(terminal_node)
        self._update_leaf_status(new_node)
        return len(remainder)

    def iter_leaves(self) -> list[TreeNode]:
        return list(self.evictable_leaves)

    def evict_until_within_budget(self) -> None:
        while self.cached_token_count > self.token_budget:
            leaves = self.iter_leaves()
            if not leaves:
                break
            victim = min(leaves, key=self.eviction_strategy.get_priority)
            self.remove_leaf(victim)

    def remove_leaf(self, node: TreeNode) -> None:
        if node.is_root or not node.is_leaf:
            raise ValueError("Only leaf nodes can be evicted")

        del node.parent.children[node.key[0]]
        self.cached_token_count -= len(node.key)
        self.evictable_leaves.discard(node)
        self._update_leaf_status(node.parent)

    def _match_prefix(
        self,
        tokens: list[int],
        access_index: int | None = None,
    ) -> tuple[int, TreeNode]:
        node = self.root
        position = 0

        while position < len(tokens):
            child = node.children.get(tokens[position])
            if child is None:
                break

            common = _common_prefix_len(child.key, tokens[position:])
            if common == len(child.key):
                if access_index is not None:
                    self._touch_node(child, access_index)
                node = child
                position += common
                continue

            split_node = self._split_node(child, common, access_index)
            if access_index is not None:
                self._touch_node(split_node, access_index)
            node = split_node
            position += common
            break

        return position, node

    def _locate_exact_node(self, tokens: list[int]) -> tuple[TreeNode, list[TreeNode]]:
        if not tokens:
            return self.root, []

        node = self.root
        path: list[TreeNode] = []
        position = 0

        while position < len(tokens):
            child = node.children.get(tokens[position])
            if child is None:
                raise ValueError("Matched prefix is not present in the radix tree")

            segment_length = len(child.key)
            if tuple(tokens[position : position + segment_length]) != child.key:
                raise ValueError("Matched prefix does not align with radix node boundaries")

            node = child
            path.append(node)
            position += segment_length

        return node, path

    def _split_node(
        self,
        child: TreeNode,
        split_len: int,
        access_index: int | None,
    ) -> TreeNode:
        if split_len <= 0 or split_len >= len(child.key):
            raise ValueError("Can only split inside an existing radix segment")

        parent = child.parent
        shared_key = child.key[:split_len]
        suffix_key = child.key[split_len:]

        new_node = TreeNode(
            key=shared_key,
            prefix=parent.prefix + shared_key,
            parent=parent,
            created_at=child.created_at if access_index is None else access_index,
            last_access_index=child.last_access_index,
            access_count=child.access_count,
            priority=child.priority,
        )
        new_node.children[suffix_key[0]] = child
        parent.children[shared_key[0]] = new_node

        child.parent = new_node
        child.key = suffix_key
        self._update_leaf_status(child)
        self._update_leaf_status(new_node)
        self._update_leaf_status(parent)
        return new_node

    def _touch_node(self, node: TreeNode, access_index: int) -> None:
        node.last_access_index = access_index
        node.access_count += 1

    def _update_leaf_status(self, node: TreeNode | None) -> None:
        if node is None or node.is_root:
            return
        if node.is_leaf:
            self.evictable_leaves.add(node)
        else:
            self.evictable_leaves.discard(node)


def _common_prefix_len(left: tuple[int, ...], right: list[int] | tuple[int, ...]) -> int:
    match_length = 0
    for left_token, right_token in zip(left, right):
        if left_token != right_token:
            break
        match_length += 1
    return match_length
