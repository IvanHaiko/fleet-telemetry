"""Prepare restricted GPS research rows from the registered F09 source only."""

from runtime.flight_analytics.gps import gps_utc_text, main, prepare

__all__ = ["gps_utc_text", "main", "prepare"]

if __name__ == "__main__":
    main()
