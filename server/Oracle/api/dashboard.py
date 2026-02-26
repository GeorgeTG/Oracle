"""Dashboard API router - aggregated statistics across sessions."""
from typing import Optional
from datetime import datetime
from collections import defaultdict
from fastapi import APIRouter, Query

from Oracle.database.models import Session, MapCompletion, MapCompletionItem, Item
from Oracle.market import PriceDB
from Oracle.tooling.logger import Logger

logger = Logger("DashboardRouter")
router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    responses={500: {"description": "Internal server error"}}
)


def _build_session_filters(
    player_name: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """Build Tortoise ORM filter kwargs from query params."""
    filters = {}
    if player_name:
        filters["player_name"] = player_name
    if start_date:
        filters["started_at__gte"] = datetime.fromisoformat(start_date)
    if end_date:
        filters["started_at__lte"] = datetime.fromisoformat(end_date)
    return filters


@router.get("/overview")
async def get_overview(
    player_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """General overview stats across all sessions."""
    try:
        filters = _build_session_filters(player_name, start_date, end_date)
        sessions = await Session.filter(**filters).all()

        if not sessions:
            return {
                "total_sessions": 0, "total_maps": 0,
                "total_playtime_hours": 0, "total_currency": 0,
                "total_exp": 0, "avg_currency_per_hour": 0,
                "avg_currency_per_map": 0, "avg_exp_per_hour": 0,
                "avg_maps_per_session": 0,
                "first_session": None, "last_session": None,
            }

        total_sessions = len(sessions)
        total_maps = sum(s.total_maps for s in sessions)
        total_time = sum(s.total_time for s in sessions)
        total_playtime_hours = total_time / 3600.0
        total_currency = sum(s.currency_total for s in sessions)
        total_exp = sum(s.exp_gained_total for s in sessions)

        avg_currency_per_hour = total_currency / total_playtime_hours if total_playtime_hours > 0 else 0
        avg_currency_per_map = total_currency / total_maps if total_maps > 0 else 0
        avg_exp_per_hour = total_exp / total_playtime_hours if total_playtime_hours > 0 else 0
        avg_maps_per_session = total_maps / total_sessions if total_sessions > 0 else 0

        first_session = min(s.started_at for s in sessions)
        last_session = max(s.started_at for s in sessions)

        return {
            "total_sessions": total_sessions,
            "total_maps": total_maps,
            "total_playtime_hours": round(total_playtime_hours, 2),
            "total_currency": round(total_currency, 2),
            "total_exp": round(total_exp, 2),
            "avg_currency_per_hour": round(avg_currency_per_hour, 2),
            "avg_currency_per_map": round(avg_currency_per_map, 2),
            "avg_exp_per_hour": round(avg_exp_per_hour, 2),
            "avg_maps_per_session": round(avg_maps_per_session, 2),
            "first_session": first_session.isoformat() if first_session else None,
            "last_session": last_session.isoformat() if last_session else None,
        }
    except Exception as e:
        logger.error(f"Error in get_overview: {e}")
        return {"error": str(e)}


@router.get("/heroes")
async def get_heroes(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    min_sessions: int = Query(1),
):
    """Per-hero (player_name) statistics."""
    try:
        filters = _build_session_filters(None, start_date, end_date)
        sessions = await Session.filter(**filters).all()

        # Group by player_name
        hero_sessions: dict[str, list] = defaultdict(list)
        for s in sessions:
            if s.player_name:
                hero_sessions[s.player_name].append(s)

        heroes = []
        for player_name, sess_list in hero_sessions.items():
            if len(sess_list) < min_sessions:
                continue

            total_maps = sum(s.total_maps for s in sess_list)
            total_time = sum(s.total_time for s in sess_list)
            total_playtime_hours = total_time / 3600.0
            total_currency = sum(s.currency_total for s in sess_list)

            avg_cph = total_currency / total_playtime_hours if total_playtime_hours > 0 else 0
            avg_cpm = total_currency / total_maps if total_maps > 0 else 0

            # Best session by currency_per_hour
            best_cph = max((s.currency_per_hour for s in sess_list), default=0)
            last_played = max(s.started_at for s in sess_list)

            heroes.append({
                "player_name": player_name,
                "total_sessions": len(sess_list),
                "total_maps": total_maps,
                "total_playtime_hours": round(total_playtime_hours, 2),
                "total_currency": round(total_currency, 2),
                "avg_currency_per_hour": round(avg_cph, 2),
                "avg_currency_per_map": round(avg_cpm, 2),
                "best_currency_per_hour": round(best_cph, 2),
                "last_played": last_played.isoformat(),
            })

        # Sort by total currency descending
        heroes.sort(key=lambda h: h["total_currency"], reverse=True)

        return {"heroes": heroes}
    except Exception as e:
        logger.error(f"Error in get_heroes: {e}")
        return {"error": str(e)}


@router.get("/items")
async def get_items(
    player_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50),
    exclude_consumed: bool = Query(True),
    sort_by: str = Query("value"),  # "value" or "quantity"
):
    """Top item drops aggregated across all maps."""
    try:
        price_db = await PriceDB.instance()

        # Build filters for MapCompletionItem via map_completion
        mc_filters = {}
        if exclude_consumed:
            mc_filters["consumed"] = False
        if player_name:
            mc_filters["map_completion__player__name"] = player_name
        if start_date:
            mc_filters["map_completion__completed_at__gte"] = datetime.fromisoformat(start_date)
        if end_date:
            mc_filters["map_completion__completed_at__lte"] = datetime.fromisoformat(end_date)

        items_qs = await MapCompletionItem.filter(
            **mc_filters, delta__gt=0
        ).prefetch_related("item", "map_completion").all()

        # Group by item
        item_agg: dict[int, dict] = {}
        for mci in items_qs:
            if not mci.item:
                continue
            iid = mci.item.item_id
            if iid not in item_agg:
                item_agg[iid] = {
                    "item_id": iid,
                    "name": mci.item.name,
                    "category": mci.item.category,
                    "total_quantity": 0,
                    "total_value": 0.0,
                    "drop_count": 0,
                    "map_ids": set(),
                }
            agg = item_agg[iid]
            agg["total_quantity"] += mci.delta
            agg["total_value"] += mci.total_price
            agg["drop_count"] += 1
            agg["map_ids"].add(mci.map_completion_id)

        # Build result list
        result = []
        total_value_all = 0.0
        for agg in item_agg.values():
            current_price = price_db.get_price(agg["item_id"])
            entry = {
                "item_id": agg["item_id"],
                "name": agg["name"],
                "category": agg["category"],
                "total_quantity": agg["total_quantity"],
                "total_value": round(agg["total_value"], 2),
                "current_price": round(current_price, 2),
                "drop_count": agg["drop_count"],
                "maps_dropped_in": len(agg["map_ids"]),
            }
            result.append(entry)
            total_value_all += agg["total_value"]

        # Sort
        sort_key = "total_value" if sort_by == "value" else "total_quantity"
        result.sort(key=lambda x: x[sort_key], reverse=True)
        result = result[:limit]

        return {
            "items": result,
            "total_value_all": round(total_value_all, 2),
        }
    except Exception as e:
        logger.error(f"Error in get_items: {e}")
        return {"error": str(e)}


@router.get("/efficiency")
async def get_efficiency(
    player_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    group_by: str = Query("day"),  # "day", "week", "month"
):
    """Session efficiency grouped by time period."""
    try:
        filters = _build_session_filters(player_name, start_date, end_date)
        sessions = await Session.filter(**filters).all()

        # Group by period
        period_data: dict[str, list] = defaultdict(list)
        for s in sessions:
            if group_by == "day":
                key = s.started_at.strftime("%Y-%m-%d")
            elif group_by == "week":
                iso = s.started_at.isocalendar()
                key = f"{iso.year}-W{iso.week:02d}"
            elif group_by == "month":
                key = s.started_at.strftime("%Y-%m")
            else:
                key = s.started_at.strftime("%Y-%m-%d")
            period_data[key].append(s)

        periods = []
        for period_key, sess_list in period_data.items():
            maps = sum(s.total_maps for s in sess_list)
            total_time = sum(s.total_time for s in sess_list)
            playtime_hours = total_time / 3600.0
            currency = sum(s.currency_total for s in sess_list)
            cph = currency / playtime_hours if playtime_hours > 0 else 0

            periods.append({
                "period": period_key,
                "sessions": len(sess_list),
                "maps": maps,
                "playtime_hours": round(playtime_hours, 2),
                "currency": round(currency, 2),
                "currency_per_hour": round(cph, 2),
            })

        # Sort by period descending
        periods.sort(key=lambda p: p["period"], reverse=True)

        # Summary
        all_currency = [p["currency"] for p in periods]
        all_playtime = [p["playtime_hours"] for p in periods]
        best = max(periods, key=lambda p: p["currency"]) if periods else None

        summary = {
            "avg_daily_currency": round(sum(all_currency) / len(all_currency), 2) if all_currency else 0,
            "avg_daily_playtime_hours": round(sum(all_playtime) / len(all_playtime), 2) if all_playtime else 0,
            "best_period": best["period"] if best else None,
            "best_currency": best["currency"] if best else 0,
        }

        return {
            "group_by": group_by,
            "periods": periods,
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"Error in get_efficiency: {e}")
        return {"error": str(e)}
