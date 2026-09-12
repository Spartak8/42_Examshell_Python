"""Catalog and embedded subjects for Exam Rank 02 (C)."""

from __future__ import annotations

from exam02_subjects import EXAM02_SUBJECTS


# level, name, kind, entry point, canonical C declaration, allowed functions
_EXERCISE_ROWS = (
    # Level 1
    (1, "first_word", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (1, "fizzbuzz", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (1, "ft_putstr", "function", "ft_putstr", "void ft_putstr(char *str);", ("write",)),
    (1, "ft_strcpy", "function", "ft_strcpy", "char *ft_strcpy(char *s1, char *s2);", ()),
    (1, "ft_strlen", "function", "ft_strlen", "int ft_strlen(char *str);", ()),
    (1, "ft_swap", "function", "ft_swap", "void ft_swap(int *a, int *b);", ()),
    (1, "repeat_alpha", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (1, "rev_print", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (1, "rot_13", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (1, "rotone", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (
        1,
        "search_and_replace",
        "program",
        "main",
        "int main(int argc, char **argv);",
        ("write", "exit"),
    ),
    (1, "ulstr", "program", "main", "int main(int argc, char **argv);", ("write",)),

    # Level 2
    (2, "alpha_mirror", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (
        2,
        "camel_to_snake",
        "program",
        "main",
        "int main(int argc, char **argv);",
        ("malloc", "free", "realloc", "write"),
    ),
    (
        2,
        "do_op",
        "program",
        "main",
        "int main(int argc, char **argv);",
        ("atoi", "printf", "write"),
    ),
    (2, "ft_atoi", "function", "ft_atoi", "int ft_atoi(const char *str);", ()),
    (
        2,
        "ft_strcmp",
        "function",
        "ft_strcmp",
        "int ft_strcmp(char *s1, char *s2);",
        (),
    ),
    (
        2,
        "ft_strcspn",
        "function",
        "ft_strcspn",
        "size_t ft_strcspn(const char *s, const char *reject);",
        (),
    ),
    (2, "ft_strdup", "function", "ft_strdup", "char *ft_strdup(char *src);", ("malloc",)),
    (
        2,
        "ft_strpbrk",
        "function",
        "ft_strpbrk",
        "char *ft_strpbrk(const char *s1, const char *s2);",
        (),
    ),
    (2, "ft_strrev", "function", "ft_strrev", "char *ft_strrev(char *str);", ()),
    (
        2,
        "ft_strspn",
        "function",
        "ft_strspn",
        "size_t ft_strspn(const char *s, const char *accept);",
        (),
    ),
    (2, "inter", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (
        2,
        "is_power_of_2",
        "function",
        "is_power_of_2",
        "int is_power_of_2(unsigned int n);",
        (),
    ),
    (2, "last_word", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (2, "max", "function", "max", "int max(int *tab, unsigned int len);", ()),
    (2, "print_bits", "function", "print_bits", "void print_bits(unsigned char octet);", ("write",)),
    (
        2,
        "reverse_bits",
        "function",
        "reverse_bits",
        "unsigned char reverse_bits(unsigned char octet);",
        (),
    ),
    (
        2,
        "snake_to_camel",
        "program",
        "main",
        "int main(int argc, char **argv);",
        ("malloc", "free", "realloc", "write"),
    ),
    (
        2,
        "swap_bits",
        "function",
        "swap_bits",
        "unsigned char swap_bits(unsigned char octet);",
        (),
    ),
    (2, "union", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (2, "wdmatch", "program", "main", "int main(int argc, char **argv);", ("write",)),

    # Level 3
    (
        3,
        "add_prime_sum",
        "program",
        "main",
        "int main(int argc, char **argv);",
        ("write", "exit"),
    ),
    (3, "epur_str", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (3, "expand_str", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (
        3,
        "ft_atoi_base",
        "function",
        "ft_atoi_base",
        "int ft_atoi_base(const char *str, int str_base);",
        (),
    ),
    (
        3,
        "ft_list_size",
        "function",
        "ft_list_size",
        "int ft_list_size(t_list *begin_list);",
        (),
    ),
    (3, "ft_range", "function", "ft_range", "int *ft_range(int start, int end);", ("malloc",)),
    (3, "ft_rrange", "function", "ft_rrange", "int *ft_rrange(int start, int end);", ("malloc",)),
    (3, "hidenp", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (
        3,
        "lcm",
        "function",
        "lcm",
        "unsigned int lcm(unsigned int a, unsigned int b);",
        (),
    ),
    (3, "paramsum", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (
        3,
        "pgcd",
        "program",
        "main",
        "int main(int argc, char **argv);",
        ("printf", "atoi", "malloc", "free"),
    ),
    (3, "print_hex", "program", "main", "int main(int argc, char **argv);", ("write",)),
    (
        3,
        "rstr_capitalizer",
        "program",
        "main",
        "int main(int argc, char **argv);",
        ("write",),
    ),
    (
        3,
        "str_capitalizer",
        "program",
        "main",
        "int main(int argc, char **argv);",
        ("write",),
    ),
    (3, "tab_mult", "program", "main", "int main(int argc, char **argv);", ("write",)),

    # Level 4
    (
        4,
        "flood_fill",
        "function",
        "flood_fill",
        "void flood_fill(char **tab, t_point size, t_point begin);",
        (),
    ),
    (
        4,
        "fprime",
        "program",
        "main",
        "int main(int argc, char **argv);",
        ("printf", "atoi"),
    ),
    (4, "ft_itoa", "function", "ft_itoa", "char *ft_itoa(int nbr);", ("malloc",)),
    (
        4,
        "ft_list_foreach",
        "function",
        "ft_list_foreach",
        "void ft_list_foreach(t_list *begin_list, void (*f)(void *));",
        (),
    ),
    (
        4,
        "ft_list_remove_if",
        "function",
        "ft_list_remove_if",
        "void ft_list_remove_if(t_list **begin_list, void *data_ref, int (*cmp)());",
        ("free",),
    ),
    (4, "ft_split", "function", "ft_split", "char **ft_split(char *str);", ("malloc",)),
    (
        4,
        "rev_wstr",
        "program",
        "main",
        "int main(int argc, char **argv);",
        ("write", "malloc", "free"),
    ),
    (
        4,
        "rostring",
        "program",
        "main",
        "int main(int argc, char **argv);",
        ("write", "malloc", "free"),
    ),
    (
        4,
        "sort_int_tab",
        "function",
        "sort_int_tab",
        "void sort_int_tab(int *tab, unsigned int size);",
        (),
    ),
    (
        4,
        "sort_list",
        "function",
        "sort_list",
        "t_list *sort_list(t_list *lst, int (*cmp)(int, int));",
        (),
    ),
)


C_EXERCISES = {
    name: {
        "level": level,
        "kind": kind,
        "entry": entry,
        "signature": signature,
        "allowed_functions": tuple(allowed_functions),
    }
    for level, name, kind, entry, signature, allowed_functions in _EXERCISE_ROWS
}


C_SIGNATURES = {
    name: metadata["signature"] for name, metadata in C_EXERCISES.items()
}

C_SUBJECTS = dict(EXAM02_SUBJECTS)
if set(C_SUBJECTS) != set(C_EXERCISES):
    missing = sorted(set(C_EXERCISES) - set(C_SUBJECTS))
    extra = sorted(set(C_SUBJECTS) - set(C_EXERCISES))
    raise RuntimeError(
        f"Embedded Exam 02 subject catalog mismatch; missing={missing}, extra={extra}"
    )


EXAM02_CONFIG = {
    "id": "exam02",
    "name": "Exam 02",
    "title": "Exam 02 — C Fundamentals",
    "language": "c",
    "extension": ".c",
    "level_points": {1: 25, 2: 25, 3: 25, 4: 25},
    "levels": {
        level: [
            {
                "name": name,
                "func": metadata["entry"],
                "kind": metadata["kind"],
            }
            for name, metadata in C_EXERCISES.items()
            if metadata["level"] == level
        ]
        for level in range(1, 5)
    },
}


__all__ = (
    "EXAM02_CONFIG",
    "C_EXERCISES",
    "C_SUBJECTS",
    "C_SIGNATURES",
)
