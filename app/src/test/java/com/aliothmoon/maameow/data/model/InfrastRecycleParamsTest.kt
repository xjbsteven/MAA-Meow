package com.aliothmoon.maameow.data.model

import com.aliothmoon.maameow.domain.enums.InfrastRoomType
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Contract: Recycler station must be user-configurable without enabling itself on legacy profiles. */
class InfrastRecycleParamsTest {
    private fun facilitiesOf(config: InfrastConfig): List<String> {
        val params = config.toTaskParams(testTaskParamContext()).single().params
        return Json.parseToJsonElement(params).jsonObject.getValue("facility")
            .jsonArray.map { it.jsonPrimitive.content }
    }

    @Test
    fun newProfileOffersAndPassesRecycleToCore() {
        assertTrue(InfrastConfig().normalizedFacilities().contains(InfrastRoomType.Recycle to true))
        assertTrue(facilitiesOf(InfrastConfig()).contains("Recycle"))
    }

    @Test
    fun legacyProfileDoesNotAccidentallyEnableRecycle() {
        val legacyRooms = InfrastRoomType.entries.filter { it != InfrastRoomType.Recycle }
            .map { it to true }
        val legacy = InfrastConfig(facilities = legacyRooms)
        assertEquals(InfrastRoomType.Recycle to false, legacy.normalizedFacilities().first {
            it.first == InfrastRoomType.Recycle
        })
        assertFalse(facilitiesOf(legacy).contains("Recycle"))
    }

    @Test
    fun recycleCheckboxControlsCoreFacilityParameter() {
        val original = InfrastConfig()
        val disabled = original.copy(facilities = original.facilities.map {
            if (it.first == InfrastRoomType.Recycle) it.first to false else it
        })
        assertFalse(facilitiesOf(disabled).contains("Recycle"))
        val enabled = disabled.copy(facilities = disabled.facilities.map {
            if (it.first == InfrastRoomType.Recycle) it.first to true else it
        })
        assertTrue(facilitiesOf(enabled).contains("Recycle"))
    }
}
