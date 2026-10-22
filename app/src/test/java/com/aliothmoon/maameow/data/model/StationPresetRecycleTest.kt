package com.aliothmoon.maameow.data.model

import com.aliothmoon.maameow.domain.enums.InfrastMode
import com.aliothmoon.maameow.domain.enums.InfrastRotationStyle
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Contract: overview preset accepts Recycle independently of the standard facility list. */
class StationPresetRecycleTest {
    private fun presetRooms(config: InfrastConfig): List<String> {
        val params = config.toTaskParams(testTaskParamContext()).single().params
        return Json.parseToJsonElement(params).jsonObject.getValue("preset")
            .jsonObject.getValue("rooms").jsonArray.map { it.jsonPrimitive.content }
    }

    @Test
    fun recycleIsSelectableAndIncludedWhenSelectingAll() {
        val layout = StationPresetLayout()
        assertTrue(StationPresetRoomList.rooms(layout).any { it.id == "Recycle" })
        assertFalse(StationPresetRoomList.defaultSelection(layout).contains("Recycle"))
        assertTrue(StationPresetRoomList.allSelection(layout).contains("Recycle"))
    }

    @Test
    fun selectedRecycleSurvivesLayoutChangesAndReachesCore() {
        val config = InfrastConfig(
            mode = InfrastMode.Rotation,
            rotationStyle = InfrastRotationStyle.StationPreset,
            presetSelectedRooms = listOf("Recycle", "Mfg2"),
        ).copy(presetLayout = StationPresetLayout(mfgCount = 1))
            .syncPresetRoomsAfterLayoutChange()

        assertEquals(listOf("Recycle"), config.presetSelectedRooms)
        assertEquals(listOf("Recycle"), presetRooms(config))
    }

    @Test
    fun legacyPresetSelectionDoesNotSilentlyAddRecycle() {
        val config = InfrastConfig(
            mode = InfrastMode.Rotation,
            rotationStyle = InfrastRotationStyle.StationPreset,
            presetSelectedRooms = listOf("Control", "Mfg1"),
        )
        assertFalse(presetRooms(config).contains("Recycle"))
    }
}
