"""
配置模块 - Config Module
集中管理所有配置项
"""

from .commands import BOT_COMMANDS, COMMAND_GROUPS, COMMAND_ALIASES
from .game_config import GachaConfig, DuelConfig, ForgeConfig, VIPConfig

__all__ = [
    "BOT_COMMANDS",
    "COMMAND_GROUPS",
    "COMMAND_ALIASES",
    "GachaConfig",
    "DuelConfig",
    "ForgeConfig",
    "VIPConfig",
]
