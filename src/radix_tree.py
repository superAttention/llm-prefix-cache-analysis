from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AccessResult:
    hit_tokens: int
    inserted_tokens: int

    @property
    def full_hit(self) -> bool:
        return self.inserted_tokens == 0


@dataclass(slots=True)
class TreeNode:
    token: int | None
    parent: "TreeNode | None" = None
    prefix: tuple[int, ...] = ()
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
        return 0 if self.is_root else 1


class RadixTree:
    def __init__(self, token_budget: int, eviction_strategy) -> None:
        self.token_budget = token_budget
        self.eviction_strategy = eviction_strategy
        self.root = TreeNode(token=None)
        self.cached_token_count = 0

    def lookup(self, tokens: list[int], access_index: int | None = None) -> AccessResult:
        node = self.root
        hit_tokens = 0

        for token in tokens:
            child = node.children.get(token)
            if child is None:
                break
            node = child
            hit_tokens += 1
            if access_index is not None:
                self._touch_node(node, access_index)

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
        node = self.root
        for token in tokens[:start_index]:
            node = node.children[token]

        inserted_tokens = 0
        for token in tokens[start_index:]:
            child = node.children.get(token)
            if child is None:
                child = TreeNode(
                    token=token,
                    parent=node,
                    prefix=node.prefix + (token,),
                    created_at=access_index,
                    last_access_index=access_index,
                    access_count=1,
                    priority=priority,
                )
                node.children[token] = child
                self.cached_token_count += 1
                inserted_tokens += 1
            else:
                self._touch_node(child, access_index)
                child.priority = priority
            node = child

        return inserted_tokens

    def iter_leaves(self) -> list[TreeNode]:
        leaves: list[TreeNode] = []
        stack = [self.root]

        while stack:
            node = stack.pop()
            if node.is_root:
                stack.extend(node.children.values())
                continue
            if node.is_leaf:
                leaves.append(node)
                continue
            stack.extend(node.children.values())

        return leaves

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

        del node.parent.children[node.token]
        self.cached_token_count -= 1

    def _touch_node(self, node: TreeNode, access_index: int) -> None:
        node.last_access_index = access_index
        node.access_count += 1
