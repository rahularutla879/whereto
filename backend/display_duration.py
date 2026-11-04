"""Shared presentation policy, mirrored by lib/duration-format.ts; never enforcement."""
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_UP

def seconds_text(value,precision='nearest'):
    if value is None:return 'Unknown'
    value=Decimal(str(value))
    if not value.is_finite() or value<0:return 'Unknown'
    total=int(value.to_integral_value(rounding={'nearest':ROUND_HALF_UP,'lower':ROUND_FLOOR,'upper':ROUND_CEILING}[precision]))
    hours,rest=divmod(total,3600);minutes,seconds=divmod(rest,60)
    return ' '.join(f'{n} {unit}' for n,unit in ((hours,'hr'),(minutes,'min'),(seconds,'sec')) if n) or '0 sec'
