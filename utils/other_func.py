import bisect


def split_list_by_letter(lst: list, letter: str) -> tuple:
    index = bisect.bisect_left(lst, letter)
    first_half = lst[:index]
    second_half = lst[index:]
    return first_half, second_half


def distribute_pairs_to_threads(pairs: list, sorted_letter: str) -> tuple:
    sorted_pairs = sorted(pairs)
    first_pairs, second_pairs = split_list_by_letter(sorted_pairs, sorted_letter)
    return first_pairs, second_pairs
