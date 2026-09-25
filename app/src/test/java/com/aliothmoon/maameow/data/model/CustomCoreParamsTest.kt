package com.aliothmoon.maameow.data.model

import com.aliothmoon.maameow.domain.enums.InfrastMode
import com.aliothmoon.maameow.domain.enums.InfrastRotationStyle
import com.aliothmoon.maameow.utils.JsonUtils
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.double
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CustomCoreParamsTest {
    private fun params(config: TaskParamProvider) =
        Json.parseToJsonElement(config.toTaskParams(testTaskParamContext()).single().params).jsonObject

    @Test fun recruitMinimumAndReserveAreIndependent() {
        val config = RecruitConfig(
            maxRecruitTimes = 4, minimumRecruitTimesEnabled = true, minimumRecruitTimes = 7,
            level3PermitReserveEnabled = true, level3PermitReserve = 8,
            preserveTagEnabled = true,
        )
        val result = params(config)
        assertEquals(4, result.getValue("minimum_recruit_times").jsonPrimitive.int)
        assertEquals(8, result.getValue("level3_recruitment_permit_reserve").jsonPrimitive.int)
        assertTrue(result.getValue("preserve_tags").jsonArray.isNotEmpty())
        assertEquals(0, params(config.copy(maxRecruitTimes = 0)).getValue("minimum_recruit_times").jsonPrimitive.int)
        assertEquals(0, params(config.copy(minimumRecruitTimesEnabled = false)).getValue("minimum_recruit_times").jsonPrimitive.int)
    }

    @Test fun legacyRecruitFlagMigratesBeforeDecode() {
        val json = JsonUtils.common
        val legacy = """{"forceConfirmToMeetTimes":true,"maxRecruitTimes":4}"""
        val migrated = json.decodeFromString<RecruitConfig>(RecruitProfileMigration.migrate(legacy, json))
        assertTrue(migrated.minimumRecruitTimesEnabled)
        assertEquals(4, migrated.minimumRecruitTimes)
        assertFalse(json.decodeFromString<RecruitConfig>(RecruitProfileMigration.migrate("""{"forceConfirmToMeetTimes":false}""", json)).minimumRecruitTimesEnabled)
        val newConfig = """{"forceConfirmToMeetTimes":true,"minimumRecruitTimesEnabled":false,"minimumRecruitTimes":2}"""
        assertFalse(json.decodeFromString<RecruitConfig>(RecruitProfileMigration.migrate(newConfig, json)).minimumRecruitTimesEnabled)
        assertEquals(migrated, json.decodeFromString<RecruitConfig>(json.encodeToString(RecruitConfig.serializer(), migrated)))
    }

    @Test fun stationPresetKeepsAuxiliaryAndFiammetta() {
        val config = InfrastConfig(
            mode = InfrastMode.Rotation, rotationStyle = InfrastRotationStyle.StationPreset,
            dormThreshold = 30,
            presetSelectedRooms = listOf("Control", "Mfg1", "Trade1"), presetRest = false,
            stationPresetDrones = StationPresetDrones(true, StationPresetDrones.Room.Trading, 1, StationPresetDrones.Order.Post),
            fiammettaRecoveryEnabled = true, fiammettaTargets = listOf("清流", "可露希尔"),
            receptionReceiveClue = false, receptionMessageBoard = true,
            dormTrustEnabled = true, dormFilterNotStationedEnabled = false,
        )
        val result = params(config)
        assertEquals(20000, result.getValue("mode").jsonPrimitive.int)
        assertEquals("station_preset", result.getValue("rotation_style").jsonPrimitive.content)
        assertEquals(0.3, result.getValue("threshold").jsonPrimitive.double, 0.000001)
        assertEquals(0.5, params(config.copy(dormThreshold = 50)).getValue("threshold").jsonPrimitive.double, 0.000001)
        assertEquals(listOf("Control", "Mfg1", "Trade1"), result.getValue("preset").jsonObject.getValue("rooms").jsonArray.map { it.jsonPrimitive.content })
        assertFalse(result.getValue("preset").jsonObject.getValue("rest").jsonPrimitive.boolean)
        assertEquals("post", result.getValue("drones").jsonObject.getValue("order").jsonPrimitive.content)
        assertTrue(result.getValue("fiammetta_recovery_enabled").jsonPrimitive.boolean)
        assertEquals(listOf("清流", "可露希尔"), result.getValue("fiammetta_targets").jsonArray.map { it.jsonPrimitive.content })
        assertFalse(result.getValue("reception_receive_clue").jsonPrimitive.boolean)
        assertFalse(result.getValue("dorm_notstationed_enabled").jsonPrimitive.boolean)
    }
    @Test fun stationPresetAuxiliaryFlagsAndLayoutSync() {
        val initial = InfrastConfig(
            mode = InfrastMode.Rotation, rotationStyle = InfrastRotationStyle.StationPreset,
            presetRest = true, stationPresetDrones = StationPresetDrones(
                true, StationPresetDrones.Room.Manufacture, 2, StationPresetDrones.Order.Pre,
            ),
            receptionMessageBoard = false, receptionClueExchange = false,
            receptionSendClue = false, originiumShardAutoReplenishment = false,
            dormTrustEnabled = false,
        )
        val result = params(initial)
        assertTrue(result.getValue("preset").jsonObject.getValue("rest").jsonPrimitive.boolean)
        assertEquals("manufacture", result.getValue("drones").jsonObject.getValue("room").jsonPrimitive.content)
        assertEquals(2, result.getValue("drones").jsonObject.getValue("index").jsonPrimitive.int)
        assertEquals("pre", result.getValue("drones").jsonObject.getValue("order").jsonPrimitive.content)
        listOf("reception_message_board", "reception_clue_exchange", "reception_send_clue", "replenish", "dorm_trust_enabled")
            .forEach { assertFalse(it, result.getValue(it).jsonPrimitive.boolean) }
        val reduced = initial.copy(presetLayout = StationPresetLayout(mfgCount = 1), presetSelectedRooms = listOf("Control", "Mfg2"))
            .syncPresetRoomsAfterLayoutChange()
        assertEquals(listOf("Control"), reduced.presetSelectedRooms)
        assertEquals(1, reduced.stationPresetDrones.index)
        assertTrue(initial.copy(presetSelectedRooms = emptyList()).syncPresetRoomsAfterLayoutChange().presetSelectedRooms.isEmpty())
    }

    @Test fun recruitMinimumClampsPersistedValues() {
        val migrated = RecruitConfig(maxRecruitTimes = 2, minimumRecruitTimesEnabled = true, minimumRecruitTimes = 4).migrate()
        assertEquals(2, migrated.minimumRecruitTimes)
        assertEquals(2, params(migrated).getValue("minimum_recruit_times").jsonPrimitive.int)
        assertEquals(1, RecruitConfig(maxRecruitTimes = 0, minimumRecruitTimes = 4).migrate().minimumRecruitTimes)
    }
    @Test fun legacyProfileMigratesWithoutDroppingStationPreset() {
        val json = JsonUtils.common
        val profile = TaskProfile(
            name = "legacy-441",
            chain = listOf(
                TaskChainNode(name = "Recruit", config = RecruitConfig(maxRecruitTimes = 4)),
                TaskChainNode(name = "Base", config = InfrastConfig(
                    mode = InfrastMode.Rotation,
                    rotationStyle = InfrastRotationStyle.StationPreset,
                    presetSelectedRooms = listOf("Control", "Mfg1"),
                )),
            ),
        )
        val root = json.parseToJsonElement(json.encodeToString(listOf(profile))).jsonArray
        val profileObject = root.single().jsonObject
        val nodes = profileObject.getValue("chain").jsonArray.mapIndexed { index, element ->
            if (index != 0) element else {
                val node = element.jsonObject
                val config = node.getValue("config").jsonObject.toMutableMap()
                config.remove("minimumRecruitTimesEnabled")
                config.remove("minimumRecruitTimes")
                config["forceConfirmToMeetTimes"] = kotlinx.serialization.json.JsonPrimitive(true)
                JsonObject(node + ("config" to JsonObject(config)))
            }
        }
        val oldData = JsonArray(listOf(JsonObject(profileObject + ("chain" to JsonArray(nodes))))).toString()
        val restored = json.decodeFromString<List<TaskProfile>>(RecruitProfileMigration.migrate(oldData, json))
        val recruit = restored.single().chain[0].config as RecruitConfig
        val base = restored.single().chain[1].config as InfrastConfig
        assertTrue(recruit.minimumRecruitTimesEnabled)
        assertEquals(4, recruit.minimumRecruitTimes)
        assertEquals(listOf("Control", "Mfg1"), base.presetSelectedRooms)
        assertEquals(InfrastRotationStyle.StationPreset, base.rotationStyle)
        assertEquals(restored, json.decodeFromString<List<TaskProfile>>(json.encodeToString(restored)))
    }
}
