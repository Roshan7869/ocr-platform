# Data dictionary — ocr-platform

Schema and placeholder content for the `field_catalog.json`. Engineering drafts from existing specs; survey owner fills in authoritative values.

**Invariant:** `FINAL_VALUE MUST NEVER EXIST WITHOUT PROVENANCE`
**Template:** `FAMILY_SURVEY_V1` · **Milestones:** R0 → R0.5 → R1 → R2

---

## 1. Schema

Each field in `field_catalog.json` has these keys:

| Key | Type | Description |
|---|---|---|
| `field_id` | string | Entity-qualified ID (e.g., `member.name`) |
| `entity_owner` | enum: `document` \| `household` \| `member` \| `education` | Entity prefix |
| `cardinality` | enum: `single` \| `repeated` | One value or list |
| `source_pages` | array[int] | Page numbers (0-indexed) |
| `template_region` | string | Reference to boundary in page YAML |
| `json_type` | enum: `string` \| `integer` \| `number` \| `boolean` \| `array` \| `object` | JSON type |
| `nullable` | boolean | Can value be null? |
| `allowed_value_states` | array[enum] | Subset of: `present` \| `absent` \| `unknown` \| `unreadable` \| `not_applicable` |
| `allowed_dispositions` | array[enum] | Subset of: `accepted` \| `review` \| `rejected` \| `errored` |
| `vocabulary_version` | string? | If coded field, version of `vocabularies.yaml` |
| `normalization_rule_version` | string | Version of normalizer profile |
| `validation_rules` | array[string] | Rule IDs from `validation_rules.yaml` |
| `linkage_requirements` | array[string]? | Other fields this links to (e.g., `member_key` for education) |

---

## 2. Document entity fields

| field_id | json_type | nullable | vocabulary | Notes |
|---|---|---|---|---|
| `document.municipality` | string | no | — | Devanagari text |
| `document.zone` | string | no | — | Devanagari text |
| `document.ward_no` | string | no | — | Devanagari text |
| `document.survey_date` | string | no | — | Date format: DD/MM/YYYY |
| `document.enumerator_id` | string | yes | — | Devanagari text |
| `document.enumerator_name` | string | yes | — | Devanagari text |

---

## 3. Household entity fields

| field_id | json_type | nullable | vocabulary | Notes |
|---|---|---|---|---|
| `household.head_name` | string | no | — | Devanagari text |
| `household.mobile` | string | no | — | 10-digit numeric |
| `household.family_structure` | string | yes | family_structure | Coded |
| `household.sanitation.sewer_connection` | boolean | no | — | Checkbox |
| `household.sanitation.septic_tank` | boolean | no | — | Checkbox |
| `household.sanitation.pit_latrine` | boolean | no | — | Checkbox |
| `household.sanitation.open_defecation` | boolean | no | — | Checkbox |
| `household.sanitation.other` | boolean | no | — | Checkbox |
| `household.sanitation.other_text` | string | yes | — | Devanagari text |
| `household.solid_waste` | string | yes | solid_waste | Coded |
| `household.electricity` | string | yes | electricity | Coded |
| `household.alternative_energy` | string | yes | alternative_energy | Coded |
| `household.drinking_water` | string | yes | drinking_water | Coded |
| `household.housing_type` | string | yes | housing_type | Coded |
| `household.housing_ownership_status` | string | yes | housing_ownership | Coded |
| `household.scheme_beneficiary.option_001` | boolean | no | — | Checkbox |
| `household.scheme_beneficiary.option_002` | boolean | no | — | Checkbox |
| `household.scheme_beneficiary.option_003` | boolean | no | — | Checkbox |
| `household.loan_taken` | boolean | no | — | Checkbox |
| `household.loan_amount` | number | yes | — | Numeric |
| `household.banking` | string | yes | banking | Coded |
| `household.mobile_network` | string | yes | mobile_network | Coded |
| `household.broadband` | boolean | no | — | Checkbox |
| `household.cctv` | boolean | no | — | Checkbox |

---

## 4. Member entity fields

| field_id | json_type | nullable | vocabulary | Notes |
|---|---|---|---|---|
| `member.name` | string | no | — | Devanagari text |
| `member.gender` | string | no | gender | Coded |
| `member.age` | integer | no | — | Years |
| `member.caste` | string | yes | caste | Coded |
| `member.religion` | string | yes | religion | Coded |
| `member.disability_lt_40` | boolean | no | — | Checkbox |
| `member.disability_ge_40` | boolean | no | — | Checkbox |
| `member.housing_type` | string | yes | housing_type | Coded |
| `member.housing_status` | string | yes | housing_status | Coded |
| `member.occupation` | string | yes | occupation | Coded |
| `member.monthly_income` | string | yes | — | Income shorthand (e.g., "1.5L", "25k") |
| `member.vehicle` | string | yes | vehicle | Coded |
| `member.relation_to_head` | string | yes | relation_to_head | Coded |
| `member.other_house_elsewhere` | boolean | no | — | Checkbox |
| `member.resident_status_code` | string | yes | resident_status | Codes 1-6 |
| `member.new_address` | string | yes | — | Devanagari text |
| `member.migration_nature` | string | yes | migration_nature | Coded |

---

## 5. Education entity fields

| field_id | json_type | nullable | vocabulary | Notes |
|---|---|---|---|---|
| `education.highest_qualification` | string | yes | qualification | Coded |
| `education.member_key` | string | no | — | Links to member row |

---

## 6. Vocabulary definitions

| vocabulary_id | Owner | Status | Notes |
|---|---|---|---|
| `family_structure` | survey | placeholder | Codes TBD |
| `solid_waste` | survey | placeholder | Codes TBD |
| `electricity` | survey | placeholder | Codes TBD |
| `alternative_energy` | survey | placeholder | Codes TBD |
| `drinking_water` | survey | placeholder | Codes TBD |
| `housing_type` | survey | placeholder | Codes TBD |
| `housing_ownership` | survey | placeholder | Codes TBD |
| `banking` | survey | placeholder | Codes TBD |
| `mobile_network` | survey | placeholder | Codes TBD |
| `gender` | survey | placeholder | Codes TBD |
| `caste` | survey | placeholder | Codes TBD |
| `religion` | survey | placeholder | Codes TBD |
| `housing_status` | survey | placeholder | Codes TBD |
| `occupation` | survey | placeholder | Codes TBD |
| `vehicle` | survey | placeholder | Codes TBD |
| `relation_to_head` | survey | placeholder | Codes TBD |
| `resident_status` | survey | placeholder | Codes 1-6 (from form legend) |
| `migration_nature` | survey | placeholder | Codes TBD |
| `qualification` | survey | placeholder | Codes TBD |

---

## 7. Format specifications

| Field | Format | Example |
|---|---|---|
| Date | DD/MM/YYYY | "27/09/2026" |
| Mobile | 10-digit numeric | "9876543210" |
| Income shorthand | Number + suffix (k/L) | "1.5L", "25k", "50000" |
| Age | Integer years | "35" |
| Boolean | true/false | true |
| Coded | String code from vocabulary | "1", "SC", "HINDU" |

---

## 8. Update log

| Date | Change |
|---|---|
| 2026-09-27 | Initial data dictionary drafted from existing specs; vocabularies are placeholders pending survey owner |
