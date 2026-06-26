package com.aliothmoon.maameow.domain.enums

/**
 * 队列轮换子模式，对应 Core `rotation_style` 与 Mac `InfrastConfiguration.RotationStyle`。
 */
enum class InfrastRotationStyle(val value: String) {
    /** 游戏内一键轮换（默认） */
    Game("game"),

    /** 进驻总览设施点预设 */
    StationPreset("station_preset"),
    ;

    companion object {
        val values = entries
    }
}
