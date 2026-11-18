"""槽位索引解码：把单个整数唯一映射到多维槽位组合。

用于「按索引取题」的数据池：同样的 index 永远得到同样的内容，
因此幂等重跑与跨库比对的指纹都稳定。
"""

from __future__ import annotations


def decode(idx: int, dims: list) -> list:
    """按混合进制把 idx 解码为每个维度上的一个取值。

    dims 为「每维的取值列表」，最后一维变化最快（与 product 的通常顺序一致）。
    """
    out = []
    for d in reversed(dims):
        idx, r = divmod(idx, len(d))
        out.append(d[r])
    return list(reversed(out))


def pool_size(dims: list) -> int:
    n = 1
    for d in dims:
        n *= len(d)
    return n
