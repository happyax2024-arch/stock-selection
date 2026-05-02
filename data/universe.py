"""Stock universe management: ST/STAR/BSE detection, stock list."""
import pandas as pd


_ST_CACHE: set | None = None


def _build_st_set(fetcher) -> set:
    """Build set of ST stock codes."""
    global _ST_CACHE
    if _ST_CACHE is not None:
        return _ST_CACHE
    try:
        spot = fetcher.get_spot_snapshot()
        st_codes = set()
        for _, row in spot.iterrows():
            name = str(row.get("name", ""))
            code = str(row.get("code", ""))
            if "ST" in name.upper():
                st_codes.add(code)
        _ST_CACHE = st_codes
    except Exception:
        _ST_CACHE = set()
    return _ST_CACHE


def clear_st_cache():
    global _ST_CACHE
    _ST_CACHE = None


def is_st_stock(code: str, fetcher=None) -> bool:
    """Check if a stock is ST/*ST by its code or name."""
    code = str(code)
    if fetcher:
        st_set = _build_st_set(fetcher)
        return code in st_set
    return False


def is_star_board(code: str) -> bool:
    """Check if stock is on STAR board (科创板, 688xxx)."""
    return str(code).startswith("688")


def is_bse_board(code: str) -> bool:
    """Check if stock is on BSE (北交所, 8xxxxx, 4xxxxx)."""
    c = str(code)
    return c.startswith("8") or c.startswith("4")


def is_chi_next(code: str) -> bool:
    """Check if stock is on ChiNext (创业板, 30xxxx)."""
    return str(code).startswith(("300", "301"))


def is_main_board(code: str) -> bool:
    """Check if stock is on main board."""
    c = str(code)
    return c.startswith(("60", "00")) and not is_chi_next(c) and not is_star_board(c)


def filter_universe(df: pd.DataFrame, exclude_st=True, exclude_star=True, exclude_bse=True) -> pd.DataFrame:
    """Filter stock DataFrame by board exclusions."""
    if "code" not in df.columns:
        return df
    mask = pd.Series(True, index=df.index)
    if exclude_st:
        mask &= ~df["code"].astype(str).apply(lambda x: is_st_stock(x))
    if exclude_star:
        mask &= ~df["code"].astype(str).apply(is_star_board)
    if exclude_bse:
        mask &= ~df["code"].astype(str).apply(is_bse_board)
    return df[mask]
