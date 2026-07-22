"""the settlement split at landing — the commission-marketplace ruling.

every order line splits into take + vendor payable the moment it lands.
the identity take + payable = net is exact (integer minor units) and is
also enforced by the table's CHECK constraint. returns unwind both sides
proportionally, capped so a fully returned line nets both sides to zero.
"""

from __future__ import annotations


def split(net_minor: int, take_rate_bps: int) -> tuple[int, int]:
    """net -> (take, payable). round-half-up on the take; identity exact."""
    if net_minor < 0:
        raise ValueError("net_minor must be >= 0")
    if not 0 <= take_rate_bps <= 10_000:
        raise ValueError("take_rate_bps must be within [0, 10000]")
    take = (net_minor * take_rate_bps + 5_000) // 10_000
    return take, net_minor - take


def unwind(
    amount_minor: int,
    line_net_minor: int,
    line_take_minor: int,
    already_reversed_take: int = 0,
    already_reversed_payable: int = 0,
) -> tuple[int, int]:
    """a refund against a line -> (take_reversed, payable_reversed).

    proportional to the line's own split, capped at what remains on each
    side, and exact: reversed take + reversed payable = amount.
    """
    if amount_minor < 0 or amount_minor > line_net_minor:
        raise ValueError("refund must be within [0, line net]")
    if line_net_minor == 0:
        return 0, 0
    take_rev = amount_minor * line_take_minor // line_net_minor
    remaining_take = line_take_minor - already_reversed_take
    take_rev = min(take_rev, remaining_take)
    payable_rev = amount_minor - take_rev
    remaining_payable = (line_net_minor - line_take_minor) - already_reversed_payable
    if payable_rev > remaining_payable:
        # shift the excess to the take side; a full return nets both to zero
        take_rev += payable_rev - remaining_payable
        payable_rev = remaining_payable
    return take_rev, payable_rev
