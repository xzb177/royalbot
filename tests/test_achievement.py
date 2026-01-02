"""
成就系统测试
"""
import pytest
from database.models import UserBinding
from plugins.achievement import (
    check_and_award_achievement,
    check_all_achievements,
    get_achievement_progress,
    get_user_titles,
    ACHIEVEMENTS
)


class TestAchievementSystem:
    """成就系统测试"""

    def test_achievement_config_exists(self):
        """测试成就配置存在"""
        assert len(ACHIEVEMENTS) > 0
        assert "duel_1" in ACHIEVEMENTS
        assert "power_100" in ACHIEVEMENTS

    def test_check_and_award_new_achievement(self, db_session):
        """测试颁发新成就"""
        user = UserBinding(
            tg_id=123456,
            emby_account="test",
            win=1  # 满足 duel_1 条件
        )
        db_session.add(user)
        db_session.commit()

        result = check_and_award_achievement(user, "duel_1", db_session)
        db_session.commit()

        assert result["new"] is True
        assert result["reward"] == 20
        assert "duel_1" in user.achievements

    def test_check_already_completed_achievement(self, db_session):
        """测试已完成的成就不会重复颁发"""
        user = UserBinding(
            tg_id=123456,
            emby_account="test",
            achievements="duel_1",  # 已完成
            win=1
        )
        db_session.add(user)
        db_session.commit()

        result = check_and_award_achievement(user, "duel_1", db_session)

        assert result["new"] is False
        assert result["reward"] == 0

    def test_check_achievement_condition_not_met(self, db_session):
        """测试条件不满足不会颁发成就"""
        user = UserBinding(
            tg_id=123456,
            emby_account="test",
            win=0  # 不满足 duel_1 条件（需要 win>=1）
        )
        db_session.add(user)
        db_session.commit()

        result = check_and_award_achievement(user, "duel_1", db_session)

        assert result["new"] is False

    def test_check_all_achievements(self, db_session):
        """测试批量检查成就"""
        user = UserBinding(
            tg_id=123456,
            emby_account="test",
            win=10,
            attack=100,
            consecutive_checkin=7
        )
        db_session.add(user)
        db_session.commit()

        new_achievements = check_all_achievements(user, db_session)
        db_session.commit()

        assert len(new_achievements) > 0
        # 应该获得 duel_1, duel_10, power_100, checkin_7
        achievement_ids = [a["name"] for a in new_achievements]
        assert len([a for a in achievement_ids if "初露锋芒" in a]) > 0

    def test_get_achievement_progress(self, db_session):
        """测试获取成就进度"""
        user = UserBinding(
            tg_id=123456,
            emby_account="test",
            achievements="duel_1,power_100",
            win=5,
            attack=100
        )
        db_session.add(user)
        db_session.commit()

        progress = get_achievement_progress(user)

        assert progress["total"] > 0
        assert progress["done"] == 2  # duel_1 和 power_100
        assert "决斗" in progress["by_category"]
        assert progress["by_category"]["决斗"]["done"] >= 1

    def test_get_user_titles(self, db_session):
        """测试获取用户称号"""
        user = UserBinding(
            tg_id=123456,
            emby_account="test",
            # 带称号的成就ID
            achievements="duel_100,power_1000,checkin_30"
        )
        db_session.add(user)
        db_session.commit()

        titles = get_user_titles(user)

        assert len(titles) > 0
        assert "决斗冠军" in titles
        assert "大魔导师" in titles

    def test_power_achievement_levels(self, db_session):
        """测试战力成就等级"""
        test_cases = [
            (100, "power_100", True),
            (500, "power_500", True),
            (1000, "power_1000", True),
            (99, "power_100", False),
        ]

        for attack, ach_id, should_pass in test_cases:
            user = UserBinding(
                tg_id=attack,  # 使用 attack 作为 tg_id 避免冲突
                emby_account=f"test_{attack}",
                attack=attack
            )
            db_session.add(user)
            db_session.commit()

            result = check_and_award_achievement(user, ach_id, db_session)
            db_session.commit()

            assert result["new"] == should_pass, f"Failed for {attack} / {ach_id}"

    def test_win_streak_achievement(self, db_session):
        """测试连胜成就"""
        user = UserBinding(
            tg_id=123456,
            emby_account="test",
            win_streak=5
        )
        db_session.add(user)
        db_session.commit()

        result = check_and_award_achievement(user, "win_streak_5", db_session)
        db_session.commit()

        assert result["new"] is True
        assert result["title"] == "热血战士"
