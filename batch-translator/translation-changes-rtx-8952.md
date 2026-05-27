# Translation Changes — Branch `rtx-8952`

Sammanfattning av alla ändringar i strängöversättningsfiler gjorda i branchen `rtx-8952`
jämfört med basbranchen (`navigation-ui`).

**Nya filer tillagda:** Tyska (DE), Franska (FR), Svenska (SV — delvis ny)  
**Befintliga filer ändrade:** Engelska (EN), Spanska (ES), Nederländska (NL)

---

## 🇬🇧 Engelska (EN)

### `androidShared/src/main/res/values/strings.xml` — Modifierad

| Strängnyckel | Innan | Efter |
|---|---|---|
| `transit_detail_info_row_serialnumber` | "Tag serial number" | "Serial number" |
| `scan_transit_found_on_other_floor_plan` | `%s` parametrar | `%1$s`/`%2$s` positionerade |
| `take_picture` | "Take Picture" | "Take Photo" |
| `error_message_error_creating_transit` | `%s\n%s` | `%1$s\n%2$s` |
| `error_message_error_updating_transit` | `%s\n%s` | `%1$s\n%2$s` |
| `error_message_error_creating_cable` | `%s\n%s` | `%1$s\n%2$s` |
| `error_message_error_updating_cable` | `%s\n%s` | `%1$s\n%2$s` |

### `inspector/src/main/res/values/strings.xml` — Modifierad

| Strängnyckel | Innan | Efter |
|---|---|---|
| `dashboard_no_inspections` | "...ask your asset **manager**..." | "...ask your asset **administrator**..." |
| `take_picture` | "Take picture" | "Take photo" |

---

## 🇩🇪 Tyska (DE) — Nya filer

Alla tyska filer lades till i sin helhet i denna branch.

| Fil | Status | Antal strängar |
|---|---|---|
| `androidShared/src/main/res/values-de/strings.xml` | **Ny** | 676 |
| `infield/src/main/res/values-de/strings.xml` | **Ny** | 90 |
| `inspector/src/main/res/values-de/strings.xml` | **Ny** | 115 |

---

## 🇪🇸 Spanska (ES)

### `androidShared/src/main/res/values-es/strings.xml` — Modifierad

| Strängnyckel | Innan | Efter |
|---|---|---|
| `empty_transit_list_text` | "este **recurso** aún no tenga" | "este **asset** aún no tenga" |
| `empty_floorplan_list_text` | "Este **recurso** no tiene" | "Este **asset** no tiene" |
| `transit_detail_info_row_serialnumber` | "Número de serie de la etiqueta" | "Número de serie" |
| `scan_transit_found_on_other_floor_plan` | `%s` parametrar | `%1$s`/`%2$s` positionerade |
| `transit_definition_insulation_not_required` | "No se requiere" | "Opcional" |
| `error_message_error_patching_asset` | "el **recurso** %s" | "el asset %s" |
| `error_message_post_maintenance_approve_entries` | "el **recurso** %s" | "el asset %s" |
| `error_message_error_fetch_cable_collection` | "colección de cables" | "agrupación de cables" |
| `error_message_error_fetching_asset_capability` | "capacidad del activo" | "permiso del Asset" |
| `error_message_error_fetching_asset_capabilities` | "capacidades del **recurso**" | "permisos del Asset" |
| `error_message_error_creating_transits` | "tránsitos" | "pasamuros" |
| `error_message_error_creating_transit` | "tránsito **%s**\n**%s**" | "pasamuros **%1$s**\n**%2$s**" |
| `error_message_error_updating_transit` | "pasatránsito **%s**\n**%s**" | "pasamuros **%1$s**\n**%2$s**" |
| `error_message_error_creating_cable` | `%s\n%s` | `%1$s\n%2$s` |
| `error_message_error_updating_cable` | `%s\n%s` | `%1$s\n%2$s` |
| `sync_error_not_found_description` | "el **recurso**" | "el asset" |
| `sync_status_fetching_asset_document_lists` | "del activo" | "del Asset" |
| `sync_status_patch_asset` | "Sincronizando **recurso**" | "Sincronizando asset" |
| `missing_token_text` | "lista de **recursos**" | "lista de assets" |
| `asset_disabled_customer_paused_message` | "acceso al **recurso**" | "acceso al asset" |

### `infield/src/main/res/values-es/strings.xml` — Modifierad

| Strängnyckel | Innan | Efter |
|---|---|---|
| `asset_remove_dialog_message` | "sus **recursos**" | "sus assets" |
| `intro_description_version_1_2_0` | "sus **recursos**" | "sus assets" |

### `inspector/src/main/res/values-es/strings.xml` — Modifierad

| Strängnyckel | Innan | Efter |
|---|---|---|
| `empty_transit_inspection_list_text` | "este **recurso**" | "este asset" |

---

## 🇫🇷 Franska (FR) — Nya filer

Alla franska filer lades till i sin helhet i denna branch.

| Fil | Status | Antal strängar |
|---|---|---|
| `androidShared/src/main/res/values-fr/strings.xml` | **Ny** | 678 |
| `infield/src/main/res/values-fr/strings.xml` | **Ny** | 90 |
| `inspector/src/main/res/values-fr/strings.xml` | **Ny** | 115 |

---

## 🇳🇱 Nederländska (NL)

### `androidShared/src/main/res/values-nl/strings.xml` — Modifierad

| Strängnyckel | Innan | Efter |
|---|---|---|
| `filter_sort_by_display_order` | "Systeemvolgorde" | "Systeemsortering" |
| `transit_detail_info_row_serialnumber` | "Tag serienummer" | "Serienummer" |
| `scan_transit_found_on_other_floor_plan` | `%s` parametrar | `%1$s`/`%2$s` positionerade |
| `transit_definition_input_y` | "J" (stavfel) | "Y" |
| `transit_definition_input_custom_front_name` | "Frontnaam" | "Naam voorkant" |
| `transit_definition_input_custom_back_name` | "Terugnaam" | "Naam achterkant" |
| `transit_definition_insulation_not_required` | "Niet nodig" | "Optioneel" |
| `error_message_error_fetching_assets` | "**resources**" (engelska) | "assets" |
| `error_message_post_task_response` | "voor **middel** %s" | "voor asset %s" |
| `error_message_post_cable_opening_status` | "voor **object** %s" | "voor asset %s" |
| `error_message_post_cable_connection_states` | "voor het **object** %s" | "voor het asset %s" |
| `error_message_post_cable_status` | "voor **object** %s" | "voor asset %s" |
| `error_message_post_maintenance_approve_entries` | "voor **object** %s" | "voor asset %s" |
| `error_message_error_fetch_cable_collection` | "kabelverzameling" | "kabelbundel" |
| `error_message_error_fetching_asset_capability` | "resourcecapaciteit" | "rechten voor het Asset" |
| `error_message_error_fetching_asset_capabilities` | "assetcapaciteiten" | "rechten voor het Asset" |
| `error_message_error_creating_transit` | `%s\n%s` | `%1$s\n%2$s` |
| `error_message_error_updating_transit` | `%s\n%s` | `%1$s\n%2$s` |
| `error_message_error_creating_cable` | `%s\n%s` | `%1$s\n%2$s` |
| `error_message_error_updating_cable` | `%s\n%s` | `%1$s\n%2$s` |
| `sync_status_fetching_asset_document_lists` | "van de **resource** ophalen" | "voor het Asset ophalen" |
| `sync_status_patch_asset` | "Synchroniseert **resurs**" (fe) | "Synchroniseert asset" |
| `state` | "Status" (fel ord) | "Land" |
| `missing_token_text` | "de **resurs**lijst" | "de assetlijst" |
| `asset_disabled_customer_paused_message` | "**Resurs**toegang" | "Assettoegang" |
| `maintenance_plans_due` | "Vervallen" (samma som Overdue) | "Vervalt" |
| `cable_opening_mark_pulled` | "ingevoerd" | "getrokken" |

### `infield/src/main/res/values-nl/strings.xml` — Modifierad

| Strängnyckel | Innan | Efter |
|---|---|---|
| `asset_remove_dialog_message` | "bijbehorende **resources**" | "bijbehorende assets" |
| `intro_description_version_1_2_0` | "uw **resources**" | "uw assets" |

### `inspector/src/main/res/values-nl/strings.xml` — Modifierad

| Strängnyckel | Innan | Efter |
|---|---|---|
| `empty_transit_inspection_list_text` | "deze **resource**" | "dit asset" |
| `inspection_closed_message` | "een **resource**beheerder" | "een assetbeheerder" |

---

## 🇸🇪 Svenska (SV)

### `androidShared/src/main/res/values-sv/strings.xml` — Modifierad (i praktiken ny)

Filen existerade sedan tidigare men innehöll i princip bara en enda sträng
(`url_roxtec_com_installation`). I denna branch lades hela den svenska översättningen
till (676 strängar). Den befintliga URL-strängen ersattes med standardattributet
`translatable="false"` istället för `tools:ignore="Untranslatable"`.

Utöver den initiala tillägget gjordes följande korrigeringar i efterföljande commits:

| Strängnyckel | Innan | Efter |
|---|---|---|
| `common_success` | "Framgång" | "Klart" |
| `filter_sort_by_display_order` | "Systembeställning" | "Systemsortering" |
| `empty_transit_list_text` | "...denna **resurs** har inga..." | "...denna **asset** har inga..." |
| `empty_floorplan_list_text` | "Denna **resurs** har inga planritningar." | "Denna **asset** har inga planritningar." |
| `empty_assets_list_title` | "Inga **resurser**" | "Inga assets" |
| `empty_assets_list_text` | "...några **resurser**..." | "...några assets..." |
| `transit_detail_set_status` | "Ange status" | "Sätt status" |
| `transit_detail_confirm_delete_transit` | "Ta bort %s" | "Radera %s" |
| `transit_detail_info_row_serialnumber` | "Märk serienummer" | "Serienummer" |
| `scan_transit_found_on_other_floor_plan` | `%s`-parametrar | `%1$s`/`%2$s` positionerade |
| `transit_definition_input_geolocation_hint` | "Vald geoplats" | "Vald geolokalisering" |
| `transit_definition_subtitle_quick_actions` | "Snabba åtgärder" | "Genvägar" |
| `transit_definition_insulation_not_required` | "Behövs ej" | "Valfri" |
| `constraint_discard` | "Förkasta ändringar" | "Kasta ändringar" |
| `take_picture` | "Ta bild" | "Ta foto" |
| `description_opening_photo` | "Genomföringsfoto" | "Öppningsfoto" |
| `error_message_error_fetching_assets` | "...av **resurser**" | "...av assets" |
| `error_message_error_patching_asset` | "av **resurs** %s" | "av asset %s" |
| `error_message_post_task_response` | "för **resurs** %s" | "för asset %s" |
| `error_message_post_cable_opening_status` | "för **resurs** %s" | "för asset %s" |
| `error_message_post_cable_connection_states` | "för **resurs** %s" | "för asset %s" |
| `error_message_post_cable_status` | "för **resurs** %s" | "för asset %s" |
| `error_message_post_maintenance_approve_entries` | "för **resurs** %s" | "för asset %s" |
| `error_message_error_fetch_cable_collection` | "kabelkollektion" | "kabelsamling" |
| `error_message_error_fetching_asset_capability` | "**resurs**kapacitet" | "behörighet för asset" |
| `error_message_error_fetching_asset_capabilities` | "**resurs**kapaciteter" | "behörigheter för asset" |
| `error_message_error_creating_transit` | `%s\n%s` | `%1$s\n%2$s` |
| `error_message_error_updating_transit` | `%s\n%s` | `%1$s\n%2$s` |
| `error_message_error_creating_cable` | `%s\n%s` | `%1$s\n%2$s` |
| `error_message_error_updating_cable` | `%s\n%s` | `%1$s\n%2$s` |
| `smokedetectors_singular` | "Brandvarnare" | "Rökdetektor" |
| `hydraulichose_singular` | "Hydraulisk slang" | "Hydraulslang" |
| `sync_status_fetching_assets` | "Hämtar **resurser**" | "Hämtar assets" |
| `sync_status_fetching_asset_document_lists` | "Hämtar **resurs**dokumentlista" | "Hämtar dokumentlista för asset" |
| `sync_status_fetching_asset_documents` | "Hämtar **resurs**dokument %s" | "Hämtar asset dokument %s" |
| `sync_status_patch_asset` | "Synkroniserar **resurs**" | "Synkroniserar asset" |
| `zip_code` | "Zip" | "Postnummer" |
| `state` | "Status" (fel ord) | "Land" |
| `missing_token_text` | "...uppdatera **resurs**listan..." | "...uppdatera asset-listan..." |
| `maintenance_plans_due` | "Förfallen" (samma som Overdue) | "Förfaller" |
| `maintenance_plans_overdue` | "Förfallen" | "Försenad" |
| `interval_months` | "%d månader" | "%d Månader" |
| `interval_years` | "%d år" | "%d År" |
| `cable_opening_mark_pulled` | "Markera som utdragen" | "Markera som dragen" |
| `cable_list_set_cable_connected_state` | "Ställ in kabelns anslutningsstatus" | "Sätt kabelns anslutningsstatus" |
| `cable_list_action_set_status` | "Ställ in status" | "Sätt status" |
| `cable_list_termination_a` | "Avslutning A" | "Kabelände A" |
| `cable_list_termination_b` | "Avslutning B" | "Kabelände B" |
| `cable_list_terminated` | "Avslutad" | "Terminerad" |

### `infield/src/main/res/values-sv/strings.xml` — Ny

Filen lades till i sin helhet (90 strängar). Därefter gjordes följande korrigeringar:

| Strängnyckel | Innan | Efter |
|---|---|---|
| `asset_remove_dialog_title` | "Ta bort **resurs** från enhet" | "Ta bort asset från enhet" |
| `asset_remove_dialog_message` | "...radera **resurs** och dess resurser..." | "...ta bort asset och dess resurser..." |
| `sync_status_not_on_device` | "Inte på enhet" | "Ej på enhet" |
| `sync_status_updating_asset` | "Uppdaterar **resurs**" | "Uppdaterar asset" |
| `opening_installation_invalid_message` | "Please set a status for %s" (engelska) | "Ange en status för %s" |
| `tap_target_set_transit_status_title` | "Ange status" | "Sätt status" |

### `inspector/src/main/res/values-sv/strings.xml` — Ny

Filen lades till i sin helhet (115 strängar). Därefter gjordes följande korrigeringar:

| Strängnyckel | Innan | Efter |
|---|---|---|
| `menu_dashboard` | "Instrumentpanel" | "Översikt" |
| `transit_detail_title_openings` | "Genomföringar" | "Öppningar" |
| `dashboard_no_inspections` | "...din **tillgångsförvaltare**..." | "...din asset administrator..." |
| `inspection_questions_title` | `{genomföringsNamn}` (svenska platshållare) | `{transitName}` |


