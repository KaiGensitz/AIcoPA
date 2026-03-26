options(repos = c(CRAN = "https://cloud.r-project.org"))

req_pkgs <- c("readxl", "dplyr", "lme4")
to_install <- req_pkgs[!req_pkgs %in% installed.packages()[, "Package"]]
if (length(to_install) > 0) {
  install.packages(to_install, repos = "https://cloud.r-project.org")
}

library(readxl)
library(dplyr)
library(lme4)

# =========================================================
# 1) Pfad zur exportnahen Datei
# =========================================================
file_path <- "//ispwserver01.unibe.ch/SPW5_Projekte/DigiK_AIcoPA/Data_Simulation/AIcoPA_simulation_v2_5_export_like_template.xlsx"
# file_path <- "C:/Users/rre00/OneDrive - Universitaet Bern/Universität/Master/FS_26/Masterarbeit/Anstellung/Data_Simulation/AIcoPA_simulation_v2_5_export_like_template.xlsx"

# =========================================================
# 2) Daten laden
# =========================================================
out <- read_excel(file_path)

cat("=====================================\n")
cat("DATEI GELADEN\n")
cat("=====================================\n")
cat("Zeilen:", nrow(out), "\n")
cat("Spalten:", ncol(out), "\n\n")

# =========================================================
# PA aus Surveydaten rekonstruieren
# =========================================================
extract_days <- function(x) {
  as.numeric(gsub("[^0-9]", "", as.character(x)))
}

out$vig_days   <- extract_days(out$Bew1)
out$mod_days   <- extract_days(out$Bew3)
out$light_days <- extract_days(out$Bew5)

out$vig_min   <- suppressWarnings(as.numeric(out$Bew2))
out$mod_min   <- suppressWarnings(as.numeric(out$Bew4))
out$light_min <- suppressWarnings(as.numeric(out$Bew6))

# MET berechnen (entsprechend Check-Definition)
out$PA_MET <- 
  ifelse(is.na(out$vig_days), 0, out$vig_days) * ifelse(is.na(out$vig_min), 0, out$vig_min) * 9 +
  ifelse(is.na(out$mod_days), 0, out$mod_days) * ifelse(is.na(out$mod_min), 0, out$mod_min) * 5 +
  ifelse(is.na(out$light_days), 0, out$light_days) * ifelse(is.na(out$light_min), 0, out$light_min) * 3

# =========================================================
# 3) Hilfsfunktionen für saubere Ausgabe
# =========================================================
print_section <- function(title) {
  cat("\n")
  cat("=====================================\n")
  cat(title, "\n")
  cat("=====================================\n")
}

make_numeric <- function(x) suppressWarnings(as.numeric(x))

check_distribution <- function(var) {
  if (var %in% names(out)) {
    cat("\nVerteilung:", var, "\n")
    print(table(out[[var]], useNA = "ifany"))
  }
}

check_filter_pair <- function(days_col, min_col) {
  if (all(c(days_col, min_col) %in% names(out))) {
    cat("\n", days_col, "vs", min_col, "\n")
    print(table(out[[days_col]], is.na(out[[min_col]]), useNA = "ifany"))
  }
}

# =========================================================
# 4) Grundstruktur prüfen
# =========================================================
print_section("1. GRUNDSTRUKTUR")

cat("Spaltennamen (erste 30):\n")
print(names(out)[1:min(30, ncol(out))])

cat("\nHauefigkeit studyGroup x timePoint:\n")
print(table(out$studyGroup, out$timePoint, useNA = "ifany"))

cat("\nAnzahl Zeilen pro ID (sollte meist 3 sein):\n")
print(table(table(out$id)))

# =========================================================
# 5) Interventionsmuster auf Outcome-Ebene
# =========================================================
print_section("2. CROSS-OVER MUSTER: PA (aus Survey berechnet)")

out %>%
  group_by(studyGroup, timePoint) %>%
  summarise(
    MET = mean(PA_MET, na.rm = TRUE),
    sd  = sd(PA_MET, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  print()

cat("\nErwartung:\n")
cat("- Gruppe 1: Anstieg T1 -> T2\n")
cat("- Gruppe 2: Anstieg T2 -> T3\n")

# =========================================================
# 6) Habit-Muster
# =========================================================
print_section("3. CROSS-OVER MUSTER: HABIT")

habit_cols <- c("Habit[Habit1]", "Habit[Habit2]", "Habit[Habit3]", "Habit[Habit4]")
habit_cols <- habit_cols[habit_cols %in% names(out)]

if (length(habit_cols) > 0) {
  out$habit_score_check <- rowMeans(out[, habit_cols], na.rm = TRUE)

  habit_summary <- out %>%
    group_by(studyGroup, timePoint) %>%
    summarise(
      n = n(),
      habit_mean = mean(habit_score_check, na.rm = TRUE),
      habit_sd   = sd(habit_score_check, na.rm = TRUE),
      .groups = "drop"
    )
  print(habit_summary)

  cat("\nErwartung:\n")
  cat("- Gruppe 1: Habit steigt von T1 auf T2\n")
  cat("- Gruppe 2: Habit steigt eher von T2 auf T3\n")
} else {
  cat("Keine Habit-Spalten gefunden.\n")
}

# =========================================================
# 7) TAM-Logik
# =========================================================
print_section("4. TAM-LOGIK")

tam_anchor <- "TAM[WA1]"

if (tam_anchor %in% names(out)) {
  tam_present <- !is.na(out[[tam_anchor]])
  tam_table <- table(out$studyGroup, out$timePoint, tam_present, useNA = "ifany")
  print(tam_table)

  cat("\nErwartung:\n")
  cat("- studyGroup 1 nur bei T2 TAM vorhanden\n")
  cat("- studyGroup 2 nur bei T3 TAM vorhanden\n")
  cat("- sonst FALSE\n")
} else {
  cat("TAM[WA1] nicht gefunden.\n")
}

# =========================================================
# 8) PA-Filterlogik
# =========================================================
print_section("5. FILTERLOGIK PA")

check_filter_pair("Bew1", "Bew2")
check_filter_pair("Bew3", "Bew4")
check_filter_pair("Bew5", "Bew6")

cat("\nErwartung:\n")
cat("- Wenn Tage = 0 oder '0 Tage', dann Minuten = NA\n")
cat("- Wenn Tage > 0, dann Minuten meist nicht NA\n")

# =========================================================
# 9) Korrelationen der Kernkonstrukte
# =========================================================
print_section("6. KORRELATIONEN DER KERNKONSTRUKTE")

corr_list <- list()

if ("Intention1[Int1]" %in% names(out)) {
  corr_list$Intention1 <- make_numeric(out[["Intention1[Int1]"]])
}
if ("Control1[Con1]" %in% names(out)) {
  corr_list$Control1 <- make_numeric(out[["Control1[Con1]"]])
}
if ("ActionPlan[ActionPlan1]" %in% names(out)) {
  corr_list$ActionPlan1 <- make_numeric(out[["ActionPlan[ActionPlan1]"]])
}
if ("Habit[Habit1]" %in% names(out)) {
  corr_list$Habit1 <- make_numeric(out[["Habit[Habit1]"]])
}

# Rekonstruierte PA immer ergänzen
corr_list$PA_MET <- out$PA_MET

if (length(corr_list) >= 2) {
  corr_df <- as.data.frame(corr_list)
  print(round(cor(corr_df, use = "pairwise.complete.obs"), 2))

  cat("\nGrobe Erwartungen:\n")
  cat("- Intention mit PA positiv\n")
  cat("- PBC mit PA positiv\n")
  cat("- Habit mit PA positiv\n")
  cat("- Planning mit PA positiv\n")
} else {
  cat("Zu wenige Korrelationsvariablen vorhanden.\n")
}

# =========================================================
# 10) Missingness
# =========================================================
print_section("7. MISSINGNESS")

missing_overall <- mean(is.na(out))
cat("Gesamter Missing-Anteil:", round(missing_overall, 3), "\n")

missing_by_time <- out %>%
  group_by(timePoint) %>%
  summarise(
    missing_share = mean(is.na(as.matrix(across(everything())))),
    .groups = "drop"
  )
print(missing_by_time)

cat("\nMissingness in zentralen Variablen:\n")
central_vars <- c(
  "zimo_discat5", "zimo_enjoy1", "zimo_enjoy2", "zimo_enjoy3",
"zimo_risk1", "zimo_risk2", "zimo_risk3"
)
central_vars <- central_vars[central_vars %in% names(out)]

for (v in central_vars) {
  cat(v, ":", round(mean(is.na(out[[v]])), 3), "\n")
}

cat("PA_MET (rekonstruiert):", round(mean(is.na(out$PA_MET)), 3), "\n")

if ("PA[MET]" %in% names(out)) {
  cat("PA[MET]:", round(mean(is.na(out[["PA[MET]"]])), 3), "\n")
}
if ("PA[steps]" %in% names(out)) {
  cat("PA[steps]:", round(mean(is.na(out[["PA[steps]"]])), 3), "\n")
}

# =========================================================
# 11) Ceiling / Floor
# =========================================================
print_section("8. CEILING / FLOOR")

check_distribution("Habit[Habit1]")
check_distribution("Intention1[Int1]")
check_distribution("Control1[Con1]")
check_distribution("ActionPlan[ActionPlan1]")
check_distribution("TAM[WA1]")

# =========================================================
# 12) Einfache LMMs
# =========================================================
print_section("9. EINFACHE LMMs")

if ("timePoint" %in% names(out)) {
  out$timePoint <- factor(out$timePoint, levels = c("T1", "T2", "T3"))
}

if ("studyGroup" %in% names(out)) {
  out$studyGroup <- factor(out$studyGroup)
}

if (length(habit_cols) > 0) {
  out$habit_score_check <- rowMeans(out[, habit_cols], na.rm = TRUE)
}

if (all(c("habit_score_check", "studyGroup", "timePoint", "id") %in% names(out))) {
  cat("\nLMM Habit:\n")
  fit_habit <- lmer(habit_score_check ~ studyGroup * timePoint + (1 | id), data = out)
  print(summary(fit_habit))
}

if (all(c("PA_MET", "studyGroup", "timePoint", "id") %in% names(out))) {
  cat("\nLMM PA_MET:\n")
  fit_pa <- lmer(PA_MET ~ studyGroup * timePoint + (1 | id), data = out)
  print(summary(fit_pa))
}

# =========================================================
# 12b) Erweiterte LMMs mit soziodemografischen Prädiktoren
# =========================================================
print_section("9b. ERWEITERTE LMMs MIT DEMOGRAFIE")

# Alter aus Geburtsjahr rekonstruieren, falls Geb existiert
if ("Geb" %in% names(out)) {
  out$age_check <- 2026 - as.numeric(out$Geb)
}

# gender rekodieren: 1 = weiblich, 0 = maennlich
if ("Ges" %in% names(out)) {
  out$female_check <- ifelse(out$Ges == "Weiblich", 1,
                             ifelse(out$Ges == "Männlich", 0, NA))
}

# prior app use rekodieren
if ("AppUseGeneral" %in% names(out)) {
  out$prior_app_check <- ifelse(out$AppUseGeneral == "Ja", 1,
                                ifelse(out$AppUseGeneral == "Nein", 0, NA))
}

# income ordinal rekodieren
if ("Einko" %in% names(out)) {
  out$income_check <- case_when(
    out$Einko %in% c("< 2000 CHF", "2000-3000 CHF") ~ 1,
    out$Einko %in% c("3000-4000 CHF", "4000-4500 CHF") ~ 2,
    out$Einko %in% c("> 4500 CHF") ~ 3,
    TRUE ~ NA_real_
  )
}

if (all(c("PA_MET", "studyGroup", "timePoint", "id",
          "age_check", "female_check", "prior_app_check", "income_check") %in% names(out))) {
  cat("\nErweitertes LMM PA_MET:\n")
  fit_pa_demo <- lmer(
    PA_MET ~ studyGroup * timePoint + age_check + female_check + prior_app_check + income_check + (1 | id),
    data = out
  )
  print(summary(fit_pa_demo))
}

if (all(c("AppUseDays", "age_check", "female_check", "prior_app_check", "income_check") %in% names(out))) {
  out$AppUseDays_num <- suppressWarnings(as.numeric(out$AppUseDays))

  app_dat <- out %>%
    filter(!is.na(AppUseDays_num))

  if (nrow(app_dat) > 0) {
    cat("\nLineares Modell AppUseDays:\n")
    fit_app_demo <- lm(
      AppUseDays_num ~ age_check + female_check + prior_app_check + income_check,
      data = app_dat
    )
    print(summary(fit_app_demo))
  }
}
