from __future__ import annotations

from dataclasses import dataclass, field

from src.paging import chunk_tokens


@dataclass(slots=True)
class AccessResult:
    hit_tokens: int
    inserted_tokens: int
    hit_blocks: int
    inserted_blocks: int

    @property
    def full_hit(self) -> bool:
        return self.inserted_blocks == 0


@dataclass(slots=True, eq=False)
class TreeNode:
    key: tuple[int, ...]
    prefix: tuple[int, ...]
    parent: "TreeNode | None" = None
    depth: int = 0
    created_at: int = -1
    last_access_index: int = -1
    access_count: int = 0
    priority: int | float = 0
    children: dict[tuple[int, ...], "TreeNode"] = field(default_factory=dict)

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def is_leaf(self) -> bool:
        return not self.children

    @property
    def token_length(self) -> int:
        return len(self.key)


class RadixTree:
    def __init__(self, block_budget: int, eviction_strategy, page_size: int = 1) -> None:
        if block_budget < 0:
            raise ValueError("block_budget must be non-negative")
        if page_size <= 0:
            raise ValueError("page_size must be positive")

        self.block_budget = block_budget
        self.eviction_strategy = eviction_strategy
        self.page_size = page_size
        self.root = TreeNode(key=(), prefix=())
        self.cached_block_count = 0
        self.evictable_leaves: set[TreeNode] = set()

    def lookup(self, tokens: list[int], access_index: int | None = None) -> AccessResult:
        node = self.root
        hit_tokens = 0
        hit_blocks = 0

        for block in chunk_tokens(tokens, self.page_size):
            child = node.children.get(block)
            if child is None:
                break
            if access_index is not None:
                self._touch_node(child, access_index)
            node = child
            hit_blocks += 1
            hit_tokens += len(block)

        total_blocks = len(chunk_tokens(tokens, self.page_size))
        return AccessResult(
            hit_tokens=hit_tokens,
            inserted_tokens=len(tokens) - hit_tokens,
            hit_blocks=hit_blocks,
            inserted_blocks=total_blocks - hit_blocks,
        )

    def access(
        self,
        tokens: list[int],
        access_index: int,
        priority: int | float = 0,
    ) -> AccessResult:
        result = self.lookup(tokens, access_index=access_index)
        self.insert_suffix(
            tokens,
            start_block_index=result.hit_blocks,
            access_index=access_index,
            priority=priority,
        )
        self.evict_until_within_budget()
        return result

    def insert_suffix(
        self,
        tokens: list[int],
        start_block_index: int,
        access_index: int,
        priority: int | float = 0,
    ) -> int:
        blocks = chunk_tokens(tokens, self.page_size)
        terminal_node, path = self._locate_exact_node(blocks[:start_block_index])
        for node in path:
            node.priority = max(node.priority, priority)

        inserted_blocks = 0
        current = terminal_node
        for block in blocks[start_block_index:]:
            new_node = TreeNode(
                key=block,
                prefix=current.prefix + block,
                parent=current,
                depth=current.depth + 1,
                created_at=access_index,
                last_access_index=access_index,
                access_count=1,
                priority=priority,
            )
            current.children[block] = new_node
            self.cached_block_count += 1
            inserted_blocks += 1
            self._update_leaf_status(current)
            self._update_leaf_status(new_node)
            current = new_node

        return inserted_blocks

    def iter_leaves(self) -> list[TreeNode]:
        return list(self.evictable_leaves)

    def evict_until_within_budget(self) -> None:
        while self.cached_block_count > self.block_budget:
            leaves = self.iter_leaves()
            if not leaves:
                break
            victim = min(leaves, key=self.eviction_strategy.get_priority)
            self.remove_leaf(victim)

    def remove_leaf(self, node: TreeNode) -> None:
        if node.is_root or not node.is_leaf:
            raise ValueError("Only leaf nodes can be evicted")

        del node.parent.children[node.key]
        self.cached_block_count -= 1
        self.evictable_leaves.discard(node)
        self._update_leaf_status(node.parent)

    def _locate_exact_node(
        self,
        blocks: list[tuple[int, ...]],
    ) -> tuple[TreeNode, list[TreeNode]]:
        node = self.root
        path: list[TreeNode] = []

        for block in blocks:
            child = node.children.get(block)
            if child is None:
                raise ValueError("Matched prefix is not present in the radix tree")
            node = child
            path.append(node)

        return node, path

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
