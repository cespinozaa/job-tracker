HEIGHT = 280
GAP = 8


def build_status_flow(
    status_counts: dict[str, int], status_labels: dict[str, str]
) -> dict | None:
    """
    Computes band geometry for a single-source flow diagram of the current
    application status distribution (rendered as inline SVG by the template).

    The source side is ordered by count (largest first) while the target side
    keeps the fixed pipeline order, so ribbons visually cross rather than
    running as flat parallel bars.
    """
    ordered = [(status, count) for status, count in status_counts.items() if count > 0]
    if not ordered:
        return None

    total = sum(count for _, count in ordered)
    available = HEIGHT - GAP * (len(ordered) - 1)

    target_slices = {}
    y = 0.0
    for status, count in ordered:
        band_height = (count / total) * available
        target_slices[status] = (round(y, 1), round(y + band_height, 1))
        y += band_height + GAP

    source_slices = {}
    y = 0.0
    for status, count in sorted(ordered, key=lambda pair: -pair[1]):
        band_height = (count / total) * available
        source_slices[status] = (round(y, 1), round(y + band_height, 1))
        y += band_height + GAP

    bands = [
        {
            "status": status,
            "label": status_labels[status],
            "count": count,
            "sy0": source_slices[status][0],
            "sy1": source_slices[status][1],
            "ty0": target_slices[status][0],
            "ty1": target_slices[status][1],
        }
        for status, count in ordered
    ]

    return {"bands": bands, "height": HEIGHT, "total": total}
