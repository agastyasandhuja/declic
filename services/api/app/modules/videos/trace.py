"""Trusted linked-list semantics, provided as immutable data to generated visuals."""


def linked_list_trace(values, events):
    links = [i + 1 if i + 1 < len(values) else None for i in range(len(values))]
    previous, current, saved = None, 0, None
    result = []
    for event in events:
        action, node = event["action"], event["node"]
        if action in {"save", "reverse", "advance"} and current != node:
            raise ValueError("Trace current pointer differs from event index")
        if action == "save":
            saved = links[current]
        elif action == "reverse":
            links[current] = previous
        elif action == "advance":
            previous, current = current, saved
        elif action == "finish":
            if current is not None or links != [None, *range(len(values) - 1)]:
                raise ValueError("Invalid terminal reversal state")
        result.append(
            {
                **event,
                "previous": previous,
                "current": current,
                "saved_next": saved,
                "links": links.copy(),
                "head": previous if action == "finish" else 0,
            }
        )
    return result
