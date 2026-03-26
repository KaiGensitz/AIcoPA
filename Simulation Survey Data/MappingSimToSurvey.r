options(repos = c(CRAN = "https://cloud.r-project.org"))

req_pkgs <- c("readxl", "openxlsx", "dplyr", "stringr")
to_install <- req_pkgs[!req_pkgs %in% installed.packages()[, "Package"]]
if (length(to_install) > 0) {
  install.packages(to_install, repos = "https://cloud.r-project.org")
}

library(readxl)
library(openxlsx)
library(dplyr)
library(stringr)

# =========================================================
# 1) Pfade
# =========================================================
template_path <- "c:/Users/rre00/OneDrive - Universitaet Bern/Universität/Master/FS_26/Masterarbeit/Anstellung/Data_Simulation/results-survey581821.xlsx"
sim_path      <- "c:/Users/rre00/OneDrive - Universitaet Bern/Universität/Master/FS_26/Masterarbeit/Anstellung/Data_Simulation/AIcoPA_simulation_v2_5_itemdata.csv"
output_path   <- "c:/Users/rre00/OneDrive - Universitaet Bern/Universität/Master/FS_26/Masterarbeit/Anstellung/Data_Simulation/AIcoPA_simulation_v2_5_export_like_template.xlsx"

# =========================================================
# 2) Daten einlesen
# =========================================================
template <- readxl::read_excel(template_path)
sim <- read.csv(sim_path, check.names = FALSE, stringsAsFactors = FALSE)

# =========================================================
# 3) Hilfsfunktionen
# =========================================================

set_if_present <- function(df, col, values) {
  if (col %in% names(df)) {
    if (length(values) == 1) values <- rep(values, nrow(df))
    df[[col]] <- values
  }
  df
}

copy_if_present <- function(df, source_df, source_col, target_col) {
  if (source_col %in% names(source_df) && target_col %in% names(df)) {
    df[[target_col]] <- source_df[[source_col]]
  }
  df
}

to_likert_label_0_4 <- function(x) {
  x <- round(as.numeric(x))
  x <- pmin(pmax(x, 0), 4)
  lab <- c(
    "0 - stimmt gar nicht",
    "1 - stimmt wenig",
    "2 - stimmt teils-teils",
    "3 - stimmt ziemlich",
    "4 - stimmt völlig"
  )
  lab[x + 1]
}

to_days_label <- function(x) {
  x <- pmin(pmax(round(as.numeric(x)), 0), 7)
  ifelse(x == 1, "1 Tag", paste0(x, " Tage"))
}

to_phone_system <- function(n) {
  sample(c("iOS", "Android"), n, replace = TRUE, prob = c(0.45, 0.55))
}

to_gender_label <- function(x) {
  ifelse(x == 1, "Weiblich", "Männlich")
}

to_yes_no <- function(x) {
  ifelse(as.numeric(x) == 1, "Ja", "Nein")
}

safe_jitter_int <- function(x, min_val, max_val, amount = 1) {
  x <- round(as.numeric(x))
  x <- x + sample(c(-amount, 0, amount), length(x), replace = TRUE, prob = c(0.2, 0.6, 0.2))
  x <- pmin(pmax(x, min_val), max_val)
  x
}

derive_stage_text <- function(total_minutes, intention_1) {
  out <- rep(NA_character_, length(total_minutes))
  high_int <- ifelse(is.na(intention_1), FALSE, intention_1 >= 5)
  active <- ifelse(is.na(total_minutes), FALSE, total_minutes >= 150)

  out[!active & !high_int] <- "Nein, und ich plane auch nicht, in den nächsten 6 Monaten regelmässig körperlich aktiv zu werden."
  out[!active & high_int]  <- "Nein, aber ich plane in den nächsten 6 Monaten regelmässig körperlich aktiv zu werden."
  out[active & !high_int]  <- "Ja, aber ich bin noch nicht seit mehr als 6 Monaten regelmässig körperlich aktiv."
  out[active & high_int]   <- "Ja, und ich bin seit mehr als 6 Monaten regelmässig körperlich aktiv."

  out
}

random_time_seconds <- function(n, low = 5, high = 40) {
  sample(low:high, n, replace = TRUE)
}

# =========================================================
# 4) Leeres Output-Template
# =========================================================
out <- as.data.frame(matrix(NA, nrow = nrow(sim), ncol = ncol(template)))
names(out) <- names(template)

n <- nrow(sim)

# =========================================================
# 5) Technische LimeSurvey-Felder
# =========================================================
now_base <- as.POSIXct("2026-03-19 10:00:00", tz = "Europe/Zurich")
start_times <- now_base + seq_len(n) * 60
end_times   <- start_times + sample(300:1800, n, replace = TRUE)

out <- set_if_present(out, "id", sim$id)
out <- set_if_present(out, "submitdate", format(end_times, "%Y-%m-%d %H:%M:%S"))
out <- set_if_present(out, "lastpage", sample(10:18, n, replace = TRUE))
out <- set_if_present(out, "startlanguage", "de")
out <- set_if_present(out, "seed", sample(100000:999999, n, replace = TRUE))
out <- set_if_present(out, "startdate", format(start_times, "%Y-%m-%d %H:%M:%S"))
out <- set_if_present(out, "datestamp", format(end_times, "%Y-%m-%d %H:%M:%S"))
out <- set_if_present(out, "refurl", NA_character_)
out <- set_if_present(out, "interviewtime", as.numeric(difftime(end_times, start_times, units = "secs")))

# =========================================================
# 6) Direkte technische / Design-Felder
# =========================================================
out <- copy_if_present(out, sim, "timePoint", "timePoint")

if ("studyGroup" %in% names(out)) {
  out$studyGroup <- ifelse(sim$studyGroup == "IG", 1, 2)
}

if ("randomGroup" %in% names(out)) {
  out$randomGroup <- ifelse(sim$studyGroup == "IG", 1, 2)
}
if ("Einv" %in% names(out)) {
  out$Einv <- "Ja"
}

# =========================================================
# 7) App / Study basic
# =========================================================
if ("AppName" %in% names(out)) {
  out$AppName <- ifelse(sim$app_use_yesno == 1, "Studien KI-App", NA)
}
if ("AppUseStudy" %in% names(out)) {
  out$AppUseStudy <- to_yes_no(sim$app_use_yesno)
}
if ("AppUseDays" %in% names(out)) {
  out$AppUseDays <- sim$app_use_days
}
if ("AppUseGeneral" %in% names(out)) {
  out$AppUseGeneral <- ifelse(sim$prior_app == 1, "Ja", "Nein")
}
if ("QualAppGeneral" %in% names(out)) {
  out$QualAppGeneral <- ifelse(sim$prior_app == 1,
                               sample(c("Apple Health", "Google Fit", "Samsung Watch", "Fitbit"), n, replace = TRUE),
                               NA)
}
if ("TransferAppDetail" %in% names(out)) {
  out$TransferAppDetail <- ifelse(sim$app_use_yesno == 1,
                                  sample(c("Täglich", "Mehrmals pro Woche", "Selten"), n, replace = TRUE),
                                  NA)
}

# =========================================================
# 8) Bew1-6 = PA Survey
# =========================================================
if ("Bew1" %in% names(out)) out$Bew1 <- to_days_label(sim$pa_vig_days)
if ("Bew2" %in% names(out)) out$Bew2 <- ifelse(sim$pa_vig_days > 0, sim$pa_vig_minutes, NA)
if ("Bew3" %in% names(out)) out$Bew3 <- to_days_label(sim$pa_mod_days)
if ("Bew4" %in% names(out)) out$Bew4 <- ifelse(sim$pa_mod_days > 0, sim$pa_mod_minutes, NA)
if ("Bew5" %in% names(out)) out$Bew5 <- to_days_label(sim$pa_light_days)
if ("Bew6" %in% names(out)) out$Bew6 <- ifelse(sim$pa_light_days > 0, sim$pa_light_minutes, NA)

# Stage of change
pa_total_minutes <- with(sim,
  ifelse(is.na(pa_vig_days), 0, pa_vig_days) * ifelse(is.na(pa_vig_minutes), 0, pa_vig_minutes) +
  ifelse(is.na(pa_mod_days), 0, pa_mod_days) * ifelse(is.na(pa_mod_minutes), 0, pa_mod_minutes) +
  ifelse(is.na(pa_light_days), 0, pa_light_days) * ifelse(is.na(pa_light_minutes), 0, pa_light_minutes)
)
if ("STG" %in% names(out)) {
  out$STG <- derive_stage_text(pa_total_minutes, sim$intention_1)
}

# =========================================================
# 9) Haupt-Mapping: Konstrukte mit direkter Entsprechung
# =========================================================
rename_map <- c(
  "habit_1" = "Habit[Habit1]",
  "habit_2" = "Habit[Habit2]",
  "habit_3" = "Habit[Habit3]",
  "habit_4" = "Habit[Habit4]",

  "intention_1" = "Intention1[Int1]",
  "intention_2" = "Intention2[Int2]",
  "intention_3" = "Intention3[Int3]",

  "attitude_1" = "Att1[Att1]",
  "attitude_2" = "Att2[Att2]",
  "attitude_3" = "Att3[Att3]",
  "attitude_4" = "Att4[Att4]",
  "attitude_5" = "Att5[Att5]",

  "norm_inj_1" = "Norm1[Norm1]",
  "norm_inj_2" = "Norm2[Norm2]",
  "norm_inj_3" = "Norm3[Norm3]",
  "norm_desc_1" = "Norm4[Norm4]",
  "norm_desc_2" = "Norm5[Norm5]",
  "norm_desc_3" = "Norm6[Norm6]",

  "pbc_1" = "Control1[Con1]",
  "pbc_2" = "Control2[Con2]",
  "pbc_3" = "Control3[Con3]",
  "pbc_4" = "Control4[Con4]",

  "motivational_comp_1" = "MotivComp[MotivComp1]",
  "motivational_comp_2" = "MotivComp[MotivComp2]",
  "motivational_comp_3" = "MotivComp[MotivComp3]",
  "motivational_comp_4" = "MotivComp[MotivComp4]",

  "action_planning_1" = "ActionPlan[ActionPlan1]",
  "action_planning_2" = "ActionPlan[ActionPlan2]",
  "action_planning_3" = "ActionPlan[ActionPlan3]",
  "action_planning_4" = "ActionPlan[ActionPlan4]",

  "self_control_1" = "VolSelf[VolSelf1]",
  "self_control_2" = "VolSelf[VolSelf2]",
  "self_control_3" = "VolSelf[VolSelf3]"
)

for (sim_name in names(rename_map)) {
  template_name <- rename_map[[sim_name]]
  if (sim_name %in% names(sim) && template_name %in% names(out)) {
    out[[template_name]] <- sim[[sim_name]]
  }
}

# =========================================================
# 10) KIM Block
# =========================================================
# Rohskala im Export als Textlabels 0-4
kim_numeric <- list(
  "KIM[IntVer1]" = sim$autonomous_mot_1,
  "KIM[IntVer2]" = sim$autonomous_mot_2,
  "KIM[IntVer3]" = sim$autonomous_mot_3,
  "KIM[wKomp1]"  = sim$autonomous_mot_4,
  "KIM[wKomp2]"  = sim$controlled_mot_1,
  "KIM[wKomp3]"  = sim$controlled_mot_2,
  "KIM[wWahl1]"  = sim$controlled_mot_3,
  "KIM[wWahl2]"  = sim$controlled_mot_4,
  "KIM[wWahl3]"  = safe_jitter_int(sim$controlled_mot_4, 0, 4, 1),
  "KIM[DrAn1]"   = safe_jitter_int(sim$controlled_mot_2, 0, 4, 1),
  "KIM[DrAn2]"   = safe_jitter_int(sim$controlled_mot_3, 0, 4, 1),
  "KIM[DrAn3]"   = safe_jitter_int(sim$controlled_mot_1, 0, 4, 1),
  "KIM[ACheck1]" = safe_jitter_int(sim$autonomous_mot_2, 0, 4, 1)
)

for (nm in names(kim_numeric)) {
  if (nm %in% names(out)) out[[nm]] <- to_likert_label_0_4(kim_numeric[[nm]])
}

# =========================================================
# 11) ZiMo / BMZI Block
# =========================================================
# Da im Simulationsdatensatz keine expliziten ZiMo-Items vorliegen,
# werden plausible Items aus motivational_comp, attitude und self_control abgeleitet.
zimo_base_fit  <- pmin(pmax(round((sim$motivational_comp_1 + sim$motivational_comp_2) / 2), 1), 5)
zimo_base_heal <- pmin(pmax(round((sim$motivational_comp_3 + sim$motivational_comp_4) / 2), 1), 5)
zimo_base_body <- pmin(pmax(round((sim$attitude_1 + sim$attitude_2) / 2), 1), 5)
zimo_base_soc  <- pmin(pmax(round((sim$attitude_3 + sim$norm_inj_1) / 2), 1), 5)
zimo_base_comp <- pmin(pmax(round((sim$self_control_1 + sim$self_control_2) / 2), 1), 5)
zimo_base_dis  <- pmin(pmax(round((sim$attitude_4 + sim$attitude_5) / 2), 1), 5)

zimo_map <- list(
  "ZiMo[discat1]" = safe_jitter_int(zimo_base_dis, 1, 5),
  "ZiMo[discat2]" = safe_jitter_int(zimo_base_dis, 1, 5),
  "ZiMo[discat3]" = safe_jitter_int(zimo_base_dis, 1, 5),
  "ZiMo[discat4]" = safe_jitter_int(zimo_base_dis, 1, 5),

  "ZiMo[fit1]" = safe_jitter_int(zimo_base_fit, 1, 5),
  "ZiMo[fit2]" = safe_jitter_int(zimo_base_fit, 1, 5),
  "ZiMo[fit3]" = safe_jitter_int(zimo_base_fit, 1, 5),

  "ZiMo[heal1]" = safe_jitter_int(zimo_base_heal, 1, 5),
  "ZiMo[heal2]" = safe_jitter_int(zimo_base_heal, 1, 5),
  "ZiMo[heal3]" = safe_jitter_int(zimo_base_heal, 1, 5),

  "ZiMo[comper1]" = safe_jitter_int(zimo_base_comp, 1, 5),
  "ZiMo[comper2]" = safe_jitter_int(zimo_base_comp, 1, 5),
  "ZiMo[comper3]" = safe_jitter_int(zimo_base_comp, 1, 5),

  "ZiMo[aes1]" = safe_jitter_int(zimo_base_body, 1, 5),
  "ZiMo[aes2]" = safe_jitter_int(zimo_base_body, 1, 5),

  "ZiMo[con1]" = safe_jitter_int(zimo_base_soc, 1, 5),
  "ZiMo[con2]" = safe_jitter_int(zimo_base_soc, 1, 5),
  "ZiMo[con3]" = safe_jitter_int(zimo_base_soc, 1, 5),
  "ZiMo[con4]" = safe_jitter_int(zimo_base_soc, 1, 5),
  "ZiMo[con5]" = safe_jitter_int(zimo_base_soc, 1, 5),

  "ZiMo[figapp1]" = safe_jitter_int(zimo_base_body, 1, 5),
  "ZiMo[figapp2]" = safe_jitter_int(zimo_base_body, 1, 5),
  "ZiMo[figapp3]" = safe_jitter_int(zimo_base_body, 1, 5),

  "ZiMo[ACheck2]" = safe_jitter_int(zimo_base_fit, 1, 5)
)

for (nm in names(zimo_map)) {
  if (nm %in% names(out)) out[[nm]] <- zimo_map[[nm]]
}

# Neue echte ZiMo-Items direkt aus der Simulation
if ("ZiMo[discat5]" %in% names(out) && "zimo_discat5" %in% names(sim)) {
  out[["ZiMo[discat5]"]] <- sim$zimo_discat5
}
if ("ZiMo[enjoy1]" %in% names(out) && "zimo_enjoy1" %in% names(sim)) {
  out[["ZiMo[enjoy1]"]] <- sim$zimo_enjoy1
}
if ("ZiMo[enjoy2]" %in% names(out) && "zimo_enjoy2" %in% names(sim)) {
  out[["ZiMo[enjoy2]"]] <- sim$zimo_enjoy2
}
if ("ZiMo[enjoy3]" %in% names(out) && "zimo_enjoy3" %in% names(sim)) {
  out[["ZiMo[enjoy3]"]] <- sim$zimo_enjoy3
}
if ("ZiMo[risk1]" %in% names(out) && "zimo_risk1" %in% names(sim)) {
  out[["ZiMo[risk1]"]] <- sim$zimo_risk1
}
if ("ZiMo[risk2]" %in% names(out) && "zimo_risk2" %in% names(sim)) {
  out[["ZiMo[risk2]"]] <- sim$zimo_risk2
}
if ("ZiMo[risk3]" %in% names(out) && "zimo_risk3" %in% names(sim)) {
  out[["ZiMo[risk3]"]] <- sim$zimo_risk3
}

# =========================================================
# 12) Demografie
# =========================================================
if ("Geb" %in% names(out)) out$Geb <- 2026 - sim$age
if ("Ges" %in% names(out)) out$Ges <- to_gender_label(sim$gender)
if ("Ges[other]" %in% names(out)) out[["Ges[other]"]] <- NA

# Ethnizität: einfache Default-Verteilung
eth_levels <- sample(c("Eu", "As", "Am", "Af", "AuNe", "LaAa", "Noe", "In"),
                     n, replace = TRUE,
                     prob = c(0.68, 0.10, 0.05, 0.05, 0.02, 0.03, 0.04, 0.03))

eth_map <- c("Eu", "As", "Am", "Af", "AuNe", "LaAa", "Noe", "In")
for (eth in eth_map) {
  main_col <- paste0("Ethn[", eth, "]")
  com_col  <- paste0("Ethn[", eth, "comment]")
  if (main_col %in% names(out)) out[[main_col]] <- ifelse(eth_levels == eth, "Ja", NA)
  if (com_col %in% names(out)) out[[com_col]] <- NA
}
if ("Ethn[other]" %in% names(out)) out[["Ethn[other]"]] <- NA
if ("Ethn[othercomment]" %in% names(out)) out[["Ethn[othercomment]"]] <- NA

if ("Wohn" %in% names(out)) out$Wohn <- sample(c("Schweiz", "Deutschland", "Österreich"), n, replace = TRUE, prob = c(0.8, 0.15, 0.05))
if ("Wohn[other]" %in% names(out)) out[["Wohn[other]"]] <- NA

if ("Edu" %in% names(out)) {
  out$Edu <- sample(c("Obligatorische Schule", "Berufsausbildung", "Matura", "Bachelor", "Master"),
                    n, replace = TRUE, prob = c(0.08, 0.28, 0.18, 0.22, 0.24))
}
if ("Prof" %in% names(out)) {
  out$Prof <- sample(c("Angestellt", "Studierend", "Selbständig", "Arbeitslos"), n, replace = TRUE,
                     prob = c(0.55, 0.25, 0.12, 0.08))
}
if ("Prof[other]" %in% names(out)) out[["Prof[other]"]] <- NA

if ("Einko" %in% names(out)) {
  out$Einko <- ifelse(
    sim$income == 1, sample(c("< 2000 CHF", "2000-3000 CHF"), n, replace = TRUE),
    ifelse(
      sim$income == 2, sample(c("3000-4000 CHF", "4000-4500 CHF"), n, replace = TRUE),
      sample(c("> 4500 CHF"), n, replace = TRUE)
    )
  )
}
if ("Einko[other]" %in% names(out)) out[["Einko[other]"]] <- NA

if ("Branche" %in% names(out)) {
  out$Branche <- sample(c("Gesundheit", "Bildung", "IT", "Büro", "Detailhandel", "Bergbau in der Mine"),
                        n, replace = TRUE)
}

# Alltag
if ("AlltagAbl[AufWa]" %in% names(out)) out[["AlltagAbl[AufWa]"]] <- sprintf("%02d:%02d", sample(5:8, n, TRUE), sample(c(0, 15, 30, 45), n, TRUE))
if ("AlltagAbl[StaProf]" %in% names(out)) out[["AlltagAbl[StaProf]"]] <- sprintf("%02d:%02d", sample(7:10, n, TRUE), sample(c(0, 15, 30, 45), n, TRUE))
if ("AlltagAbl[EndProf]" %in% names(out)) out[["AlltagAbl[EndProf]"]] <- sprintf("%02d:%02d", sample(16:20, n, TRUE), sample(c(0, 15, 30, 45), n, TRUE))
if ("AlltagAbl[BettZeit]" %in% names(out)) out[["AlltagAbl[BettZeit]"]] <- sprintf("%02d:%02d", sample(21:24, n, TRUE), sample(c(0, 15, 30, 45), n, TRUE))
if ("AlltagAbl[PausDau]" %in% names(out)) out[["AlltagAbl[PausDau]"]] <- sample(15:90, n, TRUE)
if ("AlltagAbl[FreiDau]" %in% names(out)) out[["AlltagAbl[FreiDau]"]] <- sample(30:360, n, TRUE)

# Smartphone
if ("PhoneSystem" %in% names(out)) out$PhoneSystem <- to_phone_system(n)
if ("PhoneSystem[other]" %in% names(out)) out[["PhoneSystem[other]"]] <- NA

# =========================================================
# 13) TAM
# =========================================================
tam_map <- c(
  "tam_usefulness_1" = "TAM[WA1]",
  "tam_usefulness_2" = "TAM[WA2]",
  "tam_usefulness_3" = "TAM[WA3]",
  "tam_ease_1" = "TAM[WN1]",
  "tam_ease_2" = "TAM[WN2]",
  "tam_ease_3" = "TAM[WN3]",
  "tam_enjoyment_1" = "TAM[WB1]",
  "tam_enjoyment_2" = "TAM[WB2]",
  "tam_enjoyment_3" = "TAM[WB3]",
  "tam_trust_1" = "TAM[WF1]",
  "tam_trust_2" = "TAM[WF2]",
  "tam_trust_3" = "TAM[WF3]",
  "tam_future_use_1" = "TAM[NI1]",
  "tam_future_use_2" = "TAM[NI2]",
  "tam_future_use_3" = "TAM[NI3]"
)

for (sim_name in names(tam_map)) {
  target <- tam_map[[sim_name]]
  if (sim_name %in% names(sim) && target %in% names(out)) {
    out[[target]] <- sim[[sim_name]]
  }
}

# Zusatzitems aus vorhandenen TAM-Items ableiten
if ("TAM[WN4]" %in% names(out)) out[["TAM[WN4]"]] <- safe_jitter_int(sim$tam_ease_3, 1, 7)
if ("TAM[WB4]" %in% names(out)) out[["TAM[WB4]"]] <- safe_jitter_int(sim$tam_enjoyment_3, 1, 7)
if ("TAM[WF4]" %in% names(out)) out[["TAM[WF4]"]] <- safe_jitter_int(sim$tam_trust_3, 1, 7)

if ("TAM[WV1]" %in% names(out)) out[["TAM[WV1]"]] <- safe_jitter_int(sim$tam_usefulness_1, 1, 7)
if ("TAM[WV2]" %in% names(out)) out[["TAM[WV2]"]] <- safe_jitter_int(sim$tam_usefulness_2, 1, 7)
if ("TAM[WV3]" %in% names(out)) out[["TAM[WV3]"]] <- safe_jitter_int(sim$tam_usefulness_3, 1, 7)
if ("TAM[WV4]" %in% names(out)) out[["TAM[WV4]"]] <- safe_jitter_int(sim$tam_usefulness_2, 1, 7)

if ("TAM[NI4]" %in% names(out)) out[["TAM[NI4]"]] <- safe_jitter_int(sim$tam_future_use_3, 1, 7)
if ("TAM[ACheck3]" %in% names(out)) out[["TAM[ACheck3]"]] <- safe_jitter_int(sim$tam_future_use_2, 1, 7)

# =========================================================
# TAM nur bei korrekten Zeitpunkten
# =========================================================

tam_cols <- grep("^TAM\\[", names(out), value = TRUE)

valid_tam <- (sim$studyGroup == "IG" & sim$timePoint == "T2") |
             (sim$studyGroup == "CG" & sim$timePoint == "T3")

for (cl in tam_cols) {
  out[[cl]][!valid_tam] <- NA
}

# Qualitative App-Felder
if ("QualPos" %in% names(out)) {
  out$QualPos <- ifelse(sim$app_use_yesno == 1,
                        sample(c("Motivierend", "Einfach zu nutzen", "Hilfreich", "Gute Erinnerungen"), n, replace = TRUE),
                        NA)
}
if ("QualNeg" %in% names(out)) {
  out$QualNeg <- ifelse(sim$app_use_yesno == 1,
                        sample(c("Zu viele Nachrichten", "Teilweise unklar", "Manchmal zu allgemein", "Keine negativen Punkte"),
                               n, replace = TRUE),
                        NA)
}
if ("otherAppUse" %in% names(out)) {
  out$otherAppUse <- ifelse(sim$prior_app == 1, "Ja", "Nein")
}
if ("QualOthApp" %in% names(out)) {
  out$QualOthApp <- ifelse(sim$prior_app == 1,
                           sample(c("Apple Health", "Google Fit", "Samsung Watch", "Fitbit"), n, replace = TRUE),
                           NA)
}

# =========================================================
# 14) Sonstige Felder
# =========================================================
if ("SystemLink" %in% names(out)) {
  out$SystemLink <- paste0("SYS-", sprintf("%06d", seq_len(n) + 5000))
}

if ("eMailIG" %in% names(out)) {
  out$eMailIG <- ifelse(sim$studyGroup == "IG", paste0("ig_", seq_len(n), "@study.com"), NA)
}
if ("eMailValidIG" %in% names(out)) {
  out$eMailValidIG <- ifelse(sim$studyGroup == "IG", "Ja", NA)
}
if ("eMailKG" %in% names(out)) {
  out$eMailKG <- ifelse(sim$studyGroup == "CG", paste0("cg_", seq_len(n), "@study.com"), NA)
}
if ("eMailValidKG" %in% names(out)) {
  out$eMailValidKG <- ifelse(sim$studyGroup == "CG", "Ja", NA)
}
if ("Name" %in% names(out)) {
  out$Name <- paste0("Participant_", sprintf("%04d", seq_len(n)))
}

# =========================================================
# 15) Time-Spalten
# =========================================================
time_cols <- grep("Time$", names(out), value = TRUE)

# globale Zeitblöcke
for (cl in time_cols) {
  if (all(is.na(out[[cl]]))) {
    out[[cl]] <- random_time_seconds(n, 4, 35)
  }
}

# etwas realistischere Blockzeiten für grosse Blöcke
block_defaults <- list(
  "HabitTime" = 20,
  "Intention1Time" = 8,
  "Intention2Time" = 8,
  "Intention3Time" = 8,
  "Att1Time" = 7,
  "Att2Time" = 7,
  "Att3Time" = 7,
  "Att4Time" = 7,
  "Att5Time" = 7,
  "Norm1Time" = 7,
  "Norm2Time" = 7,
  "Norm3Time" = 7,
  "Norm4Time" = 7,
  "Norm5Time" = 7,
  "Norm6Time" = 7,
  "Control1Time" = 8,
  "Control2Time" = 8,
  "Control3Time" = 8,
  "Control4Time" = 8,
  "KIMTime" = 40,
  "ZiMoTime" = 45,
  "MotivCompTime" = 18,
  "ActionPlanTime" = 18,
  "VolSelfTime" = 15,
  "GebTime" = 6,
  "GesTime" = 5,
  "EthnTime" = 12,
  "WohnTime" = 6,
  "EduTime" = 6,
  "ProfTime" = 6,
  "EinkoTime" = 6,
  "BrancheTime" = 6,
  "AlltagAblTime" = 30,
  "PhoneSystemTime" = 6,
  "AppUseGeneralTime" = 6,
  "QualAppGeneralTime" = 8,
  "AppUseStudyTime" = 6,
  "AppUseDaysTime" = 6,
  "TransferAppDetailTime" = 7,
  "TAMTime" = 55,
  "QualPosTime" = 12,
  "QualNegTime" = 12,
  "otherAppUseTime" = 6,
  "QualOthAppTime" = 8,
  "SystemLinkTime" = 4,
  "eMailIGTime" = 8,
  "eMailValidIGTime" = 4,
  "eMailKGTime" = 8,
  "eMailValidKGTime" = 4,
  "NameTime" = 5
)

for (nm in names(block_defaults)) {
  if (nm %in% names(out)) {
    out[[nm]] <- random_time_seconds(n,
                                     max(1, block_defaults[[nm]] - 3),
                                     block_defaults[[nm]] + 3)
  }
}

# =========================================================
# 16) Konsistenzregeln / strukturelle NA
# =========================================================
# App-bezogene Felder nur wenn App genutzt
app_cols <- c("AppName", "AppUseStudy", "AppUseDays", "TransferAppDetail",
              "QualPos", "QualNeg")
app_cols <- intersect(app_cols, names(out))
for (cl in app_cols) {
  out[[cl]][sim$app_use_yesno == 0 & cl %in% c("AppName", "AppUseDays", "TransferAppDetail", "QualPos", "QualNeg")] <- NA
}

# QualAppGeneral nur wenn generelle App-Nutzung
if ("QualAppGeneral" %in% names(out)) {
  out$QualAppGeneral[sim$prior_app == 0] <- NA
}

# E-Mail-Felder nur gruppenspezifisch
if ("eMailIG" %in% names(out)) out$eMailIG[sim$studyGroup != "IG"] <- NA
if ("eMailValidIG" %in% names(out)) out$eMailValidIG[sim$studyGroup != "IG"] <- NA
if ("eMailKG" %in% names(out)) out$eMailKG[sim$studyGroup != "CG"] <- NA
if ("eMailValidKG" %in% names(out)) out$eMailValidKG[sim$studyGroup != "CG"] <- NA

# timePoint-Reihenfolge festlegen
if ("timePoint" %in% names(out)) {
  out$timePoint <- factor(out$timePoint, levels = c("T1", "T2", "T3"))
}

# Nach Teilnehmer und Messzeitpunkt sortieren
sort_cols <- intersect(c("id", "timePoint"), names(out))
if (length(sort_cols) == 2) {
  out <- out[order(out$id, out$timePoint), ]
}

# Faktor wieder in Text zurück
if ("timePoint" %in% names(out)) {
  out$timePoint <- as.character(out$timePoint)
}

# Zeilennamen zurücksetzen
rownames(out) <- NULL

# =========================================================
# Time-Spalten entfernen
# =========================================================

time_cols <- grep("Time$", names(out), value = TRUE)

out <- out[, !names(out) %in% time_cols]

# =========================================================
# 18) Export
# =========================================================
openxlsx::write.xlsx(out, output_path, overwrite = TRUE)
cat("Export-nahe Datei gespeichert unter:\n", output_path, "\n")