package com.aliothmoon.maameow.data.model

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.intOrNull

/** Migrates the retired forceConfirmToMeetTimes flag before profile decoding. */
object RecruitProfileMigration {
    fun migrate(content: String, json: Json): String {
        val root = json.parseToJsonElement(content)
        val migrated = migrateElement(root)
        return if (migrated == root) content else migrated.toString()
    }

    private fun migrateElement(element: JsonElement): JsonElement = when (element) {
        is JsonArray -> JsonArray(element.map(::migrateElement))
        is JsonObject -> {
            val values = element.mapValues { (_, value) -> migrateElement(value) }.toMutableMap()
            if ("forceConfirmToMeetTimes" in values && "minimumRecruitTimesEnabled" !in values && "minimumRecruitTimes" !in values) {
                val enabled = values["forceConfirmToMeetTimes"] == JsonPrimitive(true)
                values["minimumRecruitTimesEnabled"] = JsonPrimitive(enabled)
                if (enabled) {
                    val max = (values["maxRecruitTimes"] as? JsonPrimitive)?.intOrNull ?: 4
                    values["minimumRecruitTimes"] = JsonPrimitive(max.coerceAtLeast(1))
                }
            }
            values.remove("forceConfirmToMeetTimes")
            JsonObject(values)
        }
        else -> element
    }
}
