"""
献立生成ロジックのテスト
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.menu_generator import WeeklyMenuGenerator
from src.notion_client import ProposedDish


class TestWeekRangeCalculation:
    """週範囲計算のテスト"""

    def test_get_next_week_range_from_monday(self):
        """月曜日からの次週計算"""
        with patch.object(WeeklyMenuGenerator, "__init__", lambda x, **kwargs: None):
            generator = WeeklyMenuGenerator()

            # 2024年1月15日（月曜）を基準にすると次週は1/22-1/28
            monday = date(2024, 1, 15)
            start, end = generator._get_next_week_range(monday)

            assert start == date(2024, 1, 22)  # 次の月曜日
            assert end == date(2024, 1, 28)  # 次の日曜日

    def test_get_next_week_range_from_saturday(self):
        """土曜日からの次週計算"""
        with patch.object(WeeklyMenuGenerator, "__init__", lambda x, **kwargs: None):
            generator = WeeklyMenuGenerator()

            # 2024年1月13日（土曜）を基準にすると次週は1/15-1/21
            saturday = date(2024, 1, 13)
            start, end = generator._get_next_week_range(saturday)

            assert start == date(2024, 1, 15)  # 次の月曜日
            assert end == date(2024, 1, 21)  # 次の日曜日

    def test_get_next_week_range_from_sunday(self):
        """日曜日からの次週計算"""
        with patch.object(WeeklyMenuGenerator, "__init__", lambda x, **kwargs: None):
            generator = WeeklyMenuGenerator()

            # 2024年1月14日（日曜）を基準にすると次週は1/15-1/21
            sunday = date(2024, 1, 14)
            start, end = generator._get_next_week_range(sunday)

            assert start == date(2024, 1, 15)  # 次の月曜日
            assert end == date(2024, 1, 21)  # 次の日曜日


class TestDateRangeGeneration:
    """日付範囲生成のテスト"""

    def test_get_date_range(self):
        """日付リストの生成"""
        with patch.object(WeeklyMenuGenerator, "__init__", lambda x, **kwargs: None):
            generator = WeeklyMenuGenerator()

            start = date(2024, 1, 15)
            end = date(2024, 1, 21)
            dates = generator._get_date_range(start, end)

            assert len(dates) == 7
            assert dates[0] == date(2024, 1, 15)
            assert dates[-1] == date(2024, 1, 21)


class TestDatesWithPlans:
    """予定がある日付の抽出テスト"""

    def test_get_dates_with_plans_confirmed(self):
        """確定済みの予定がある日付"""
        with patch.object(WeeklyMenuGenerator, "__init__", lambda x, **kwargs: None):
            generator = WeeklyMenuGenerator()

            dishes = [
                ProposedDish(
                    id="1",
                    dish_name="外食",
                    date=date(2024, 1, 15),
                    category="その他",
                    status="確定",
                ),
                ProposedDish(
                    id="2",
                    dish_name="提案メニュー",
                    date=date(2024, 1, 16),
                    category="主菜",
                    status="提案",  # 提案はカウントしない
                ),
            ]

            dates = generator._get_dates_with_plans(dishes)

            assert date(2024, 1, 15) in dates
            assert date(2024, 1, 16) not in dates

    def test_get_dates_with_plans_eating_out(self):
        """外食予定がある日付"""
        with patch.object(WeeklyMenuGenerator, "__init__", lambda x, **kwargs: None):
            generator = WeeklyMenuGenerator()

            dishes = [
                ProposedDish(
                    id="1",
                    dish_name="外食",
                    date=date(2024, 1, 17),
                    category="その他",
                    status="外食・予定あり",
                ),
            ]

            dates = generator._get_dates_with_plans(dishes)

            assert date(2024, 1, 17) in dates

    def test_get_dates_with_plans_empty(self):
        """予定がない場合"""
        with patch.object(WeeklyMenuGenerator, "__init__", lambda x, **kwargs: None):
            generator = WeeklyMenuGenerator()

            dates = generator._get_dates_with_plans([])

            assert len(dates) == 0
