package com.aliothmoon.maameow.data.model

import kotlinx.serialization.Serializable

@Serializable
data class StationPresetLayout(
    val mfgCount: Int = 2,
    val tradeCount: Int = 1,
    val powerCount: Int = 3,
) {
    fun clamp(): StationPresetLayout = copy(
        mfgCount = mfgCount.coerceIn(MFG_RANGE),
        tradeCount = tradeCount.coerceIn(TRADE_RANGE),
        powerCount = powerCount.coerceIn(POWER_RANGE),
    )

    companion object {
        val MFG_RANGE = 1..5
        val TRADE_RANGE = 1..5
        val POWER_RANGE = 1..3
    }
}

@Serializable
data class StationPresetDrones(
    val enable: Boolean = false,
    val room: Room = Room.Manufacture,
    val index: Int = 1,
    val order: Order = Order.Pre,
) {
    @Serializable
    enum class Room(val apiValue: String) {
        Manufacture("manufacture"),
        Trading("trading"),
    }

    @Serializable
    enum class Order(val apiValue: String) {
        Pre("pre"),
        Post("post"),
    }
}

data class StationPresetRoom(
    val id: String,
)

object StationPresetRoomList {
    fun rooms(layout: StationPresetLayout): List<StationPresetRoom> {
        val clamped = layout.clamp()
        val list = mutableListOf(
            StationPresetRoom("Control"),
            StationPresetRoom("Reception"),
        )
        for (index in 1..clamped.mfgCount) {
            list += StationPresetRoom("Mfg$index")
        }
        for (index in 1..clamped.tradeCount) {
            list += StationPresetRoom("Trade$index")
        }
        for (index in 1..clamped.powerCount) {
            list += StationPresetRoom("Power$index")
        }
        list += StationPresetRoom("Office")
        return list
    }

    fun defaultSelection(layout: StationPresetLayout): List<String> =
        rooms(layout).map { it.id }

    fun pruneSelection(selection: List<String>, layout: StationPresetLayout): List<String> {
        val valid = rooms(layout).map { it.id }.toSet()
        return selection.filter { it in valid }
    }
}

fun InfrastConfig.syncPresetRoomsAfterLayoutChange(): InfrastConfig {
    val layout = presetLayout.clamp()
    val pruned = StationPresetRoomList.pruneSelection(presetSelectedRooms, layout)
    val rooms = if (pruned.isEmpty()) {
        StationPresetRoomList.defaultSelection(layout)
    } else {
        pruned
    }
    val maxDroneIndex = when (stationPresetDrones.room) {
        StationPresetDrones.Room.Manufacture -> layout.mfgCount
        StationPresetDrones.Room.Trading -> layout.tradeCount
    }
    val drones = if (stationPresetDrones.index > maxDroneIndex) {
        stationPresetDrones.copy(index = maxDroneIndex)
    } else {
        stationPresetDrones
    }
    return copy(presetLayout = layout, presetSelectedRooms = rooms, stationPresetDrones = drones)
}
