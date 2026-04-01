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
file_path <- "//ispwserver01.unibe.ch/SPW5_Projekte/DigiK_AIcoPA/Data_Simulation/AIcoPA_simulation_v3_export_like_template.xlsx"
# file_path <- "C:/Users/rre00/OneDrive - Universitaet Bern/Universität/Master/FS_26/Masterarbeit/Anstellung/Data_Simulation/AIcoPA_simulation_v3_export_like_template.xlsx"

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
# 3) PA aus Surveydaten rekonstruieren
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

out$PA_MET <-
  ifelse(is.na(out$vig_days), 0, out$vig_days) * ifelse(is.na(out$vig_min), 0, out$vig_min) * 9 +
  ifelse(is.na(out$mod_days), 0, out$mod_days) * ifelse(is.na(out$mod_min), 0, out$mod_min) * 5 +
  ifelse(is.na(out$light_days), 0, out$light_days) * ifelse(is.na(out$light_min), 0, out$light_min) * 3

# =========================================================
# 4) Hilfsfunktionen
# =========================================================
print_section <- function(title) {
  cat("\n")
  cat("=====================================\n")
  cat(title, "\n")
  cat("=====================================\n")
}

make_numeric <- function(x) {
  if (is.numeric(x)) return(x)
  x_chr <- as.character(x)
  x_chr <- trimws(x_chr)
  out <- suppressWarnings(as.numeric(sub("^([0-9]+).*$", "\\1", x_chr)))
  out
}

check_distribution <- function(var) {
  if (var %in% names(out)) {
    cat("\nVerteilung:", var, "\n")
    print(table(out[[var]], useNA = "ifany"))
  }
}

check_filter_pair <- function(days_col, min_col) {
  if (all(c(days_col, min_col) %in% names(out))) {
    cat("\n", days_col, "vs", min_col, "\n", sep = "")
    print(table(out[[days_col]], is.na(out[[min_col]]), useNA = "ifany"))
  }
}

# =========================================================
# 5) Grundstruktur
# =========================================================
print_section("1. GRUNDSTRUKTUR")

cat("Spaltennamen (erste 30):\n")
print(names(out)[1:min(30, ncol(out))])

cat("\nHauefigkeit studyGroup x timePoint:\n")
print(table(out$studyGroup, out$timePoint, useNA = "ifany"))

cat("\nAnzahl Zeilen pro ID:\n")
print(table(table(out$id)))

# =========================================================
# 6) Cross-over Muster: PA
# =========================================================
print_section("2. CROSS-OVER MUSTER: PA (aus Survey berechnet)")

out %>%
  group_by(studyGroup, timePoint) %>%
  summarise(
    n = n(),
    MET_mean = mean(PA_MET, na.rm = TRUE),
    MET_sd   = sd(PA_MET, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  print()

# =========================================================
# 7) Cross-over Muster: Habit
# =========================================================
print_section("3. CROSS-OVER MUSTER: HABIT")

habit_cols <- c("Habit[Habit1]", "Habit[Habit2]", "Habit[Habit3]", "Habit[Habit4]")
habit_cols <- habit_cols[habit_cols %in% names(out)]

if (length(habit_cols) > 0) {
  out$habit_score_check <- rowMeans(out[, habit_cols], na.rm = TRUE)

  out %>%
    group_by(studyGroup, timePoint) %>%
    summarise(
      n = n(),
      habit_mean = mean(habit_score_check, na.rm = TRUE),
      habit_sd   = sd(habit_score_check, na.rm = TRUE),
      .groups = "drop"
    ) %>%
    print()
} else {
  cat("Keine Habit-Spalten gefunden.\n")
}

# =========================================================
# 8) TAM-Logik
# =========================================================
print_section("4. TAM-LOGIK")

tam_anchor <- "TAM[WA1]"

if (tam_anchor %in% names(out)) {
  tam_present <- !is.na(out[[tam_anchor]])
  print(table(out$studyGroup, out$timePoint, tam_present, useNA = "ifany"))
} else {
  cat("TAM[WA1] nicht gefunden.\n")
}

# =========================================================
# 9) PA-Filterlogik
# =========================================================
print_section("5. FILTERLOGIK PA")

check_filter_pair("Bew1", "Bew2")
check_filter_pair("Bew3", "Bew4")
check_filter_pair("Bew5", "Bew6")

# =========================================================
# 10) Korrelationen der Kernkonstrukte (Skalenmittelwerte)
# =========================================================
print_section("6. KORRELATIONEN DER KERNKONSTRUKTE")

make_numeric <- function(x) {
  if (is.numeric(x)) return(x)
  x_chr <- as.character(x)
  x_chr <- trimws(x_chr)
  suppressWarnings(as.numeric(sub("^([0-9]+).*$", "\\1", x_chr)))
}

rowmean_if_exists <- function(df, cols) {
  cols <- cols[cols %in% names(df)]
  if (length(cols) == 0) return(rep(NA_real_, nrow(df)))
  tmp <- as.data.frame(lapply(df[, cols, drop = FALSE], make_numeric))
  rowMeans(tmp, na.rm = TRUE)
}

corr_df <- data.frame(
  Habit = rowmean_if_exists(out, c("Habit[Habit1]", "Habit[Habit2]", "Habit[Habit3]", "Habit[Habit4]")),
  Intention = rowmean_if_exists(out, c("Intention1[Int1]", "Intention2[Int2]", "Intention3[Int3]")),
  Attitude = rowmean_if_exists(out, c("Att1[Att1]", "Att2[Att2]", "Att3[Att3]", "Att4[Att4]", "Att5[Att5]")),
  InjNorm = rowmean_if_exists(out, c("Norm1[Norm1]", "Norm2[Norm2]", "Norm3[Norm3]")),
  DescNorm = rowmean_if_exists(out, c("Norm4[Norm4]", "Norm5[Norm5]", "Norm6[Norm6]")),
  PBC = rowmean_if_exists(out, c("Control1[Con1]", "Control2[Con2]", "Control3[Con3]", "Control4[Con4]")),

  Intrinsic = rowmean_if_exists(out, c("KIM[IntVer1]", "KIM[IntVer2]", "KIM[IntVer3]")),
  PercComp = rowmean_if_exists(out, c("KIM[wKomp1]", "KIM[wKomp2]", "KIM[wKomp3]")),
  PercChoice = rowmean_if_exists(out, c("KIM[wWahl1]", "KIM[wWahl2]", "KIM[wWahl3]")),
  Extrinsic = rowmean_if_exists(out, c("KIM[DrAn1]", "KIM[DrAn2]", "KIM[DrAn3]")),

  ActionPlan = rowmean_if_exists(out, c("ActionPlan[ActionPlan1]", "ActionPlan[ActionPlan2]", "ActionPlan[ActionPlan3]", "ActionPlan[ActionPlan4]")),
  MotivComp = rowmean_if_exists(out, c("MotivComp[MotivComp1]", "MotivComp[MotivComp2]", "MotivComp[MotivComp3]", "MotivComp[MotivComp4]")),
  VolSelf = rowmean_if_exists(out, c("VolSelf[VolSelf1]", "VolSelf[VolSelf2]", "VolSelf[VolSelf3]")),

  BMZI_discat = rowmean_if_exists(out, c("ZiMo[discat1]", "ZiMo[discat2]", "ZiMo[discat3]", "ZiMo[discat4]")),
  BMZI_fit = rowmean_if_exists(out, c("ZiMo[fit1]", "ZiMo[fit2]", "ZiMo[fit3]")),
  BMZI_heal = rowmean_if_exists(out, c("ZiMo[heal1]", "ZiMo[heal2]", "ZiMo[heal3]")),
  BMZI_comper = rowmean_if_exists(out, c("ZiMo[comper1]", "ZiMo[comper2]", "ZiMo[comper3]")),
  BMZI_aes = rowmean_if_exists(out, c("ZiMo[aes1]", "ZiMo[aes2]")),
  BMZI_con = rowmean_if_exists(out, c("ZiMo[con1]", "ZiMo[con2]", "ZiMo[con3]", "ZiMo[con4]", "ZiMo[con5]")),
  BMZI_figapp = rowmean_if_exists(out, c("ZiMo[figapp1]", "ZiMo[figapp2]", "ZiMo[figapp3]")),

  TAM_WA = rowmean_if_exists(out, c("TAM[WA1]", "TAM[WA2]", "TAM[WA3]")),
  TAM_WN = rowmean_if_exists(out, c("TAM[WN1]", "TAM[WN2]", "TAM[WN3]")),
  TAM_WB = rowmean_if_exists(out, c("TAM[WB1]", "TAM[WB2]", "TAM[WB3]")),
  TAM_WF = rowmean_if_exists(out, c("TAM[WF1]", "TAM[WF2]", "TAM[WF3]")),
  TAM_NI = rowmean_if_exists(out, c("TAM[NI1]", "TAM[NI2]", "TAM[NI3]")),

  PA_MET = out$PA_MET
)

# Variablen entfernen, die komplett NA sind
corr_df <- corr_df[, colSums(!is.na(corr_df)) > 0, drop = FALSE]

if (ncol(corr_df) >= 2) {
  print(round(cor(corr_df, use = "pairwise.complete.obs"), 2))
} else {
  cat("Zu wenige Korrelationsvariablen vorhanden.\n")
}

# =========================================================
# 11) Missingness
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

missing_vars <- c(
  "PA_MET",
  "Habit[Habit1]", "Habit[Habit2]", "Habit[Habit3]", "Habit[Habit4]",
  "Intention1[Int1]", "Intention2[Int2]", "Intention3[Int3]",
  "Control1[Con1]", "Control2[Con2]", "Control3[Con3]", "Control4[Con4]",
  "ActionPlan[ActionPlan1]", "ActionPlan[ActionPlan2]", "ActionPlan[ActionPlan3]", "ActionPlan[ActionPlan4]",
  "KIM[IntVer1]", "KIM[IntVer2]", "KIM[IntVer3]",
  "KIM[wKomp1]", "KIM[wKomp2]", "KIM[wKomp3]",
  "KIM[wWahl1]", "KIM[wWahl2]", "KIM[wWahl3]",
  "KIM[DrAn1]", "KIM[DrAn2]", "KIM[DrAn3]",
  "MotivComp[MotivComp1]", "MotivComp[MotivComp2]", "MotivComp[MotivComp3]", "MotivComp[MotivComp4]",
  "VolSelf[VolSelf1]", "VolSelf[VolSelf2]", "VolSelf[VolSelf3]",
  "ZiMo[discat1]", "ZiMo[discat2]", "ZiMo[discat3]", "ZiMo[discat4]",
  "ZiMo[fit1]", "ZiMo[fit2]", "ZiMo[fit3]",
  "ZiMo[heal1]", "ZiMo[heal2]", "ZiMo[heal3]",
  "ZiMo[comper1]", "ZiMo[comper2]", "ZiMo[comper3]",
  "ZiMo[aes1]", "ZiMo[aes2]",
  "ZiMo[con1]", "ZiMo[con2]", "ZiMo[con3]", "ZiMo[con4]", "ZiMo[con5]",
  "ZiMo[figapp1]", "ZiMo[figapp2]", "ZiMo[figapp3]",
  "TAM[WA1]", "TAM[WA2]", "TAM[WA3]",
  "TAM[WN1]", "TAM[WN2]", "TAM[WN3]",
  "TAM[WB1]", "TAM[WB2]", "TAM[WB3]",
  "TAM[WF1]", "TAM[WF2]", "TAM[WF3]",
  "TAM[NI1]", "TAM[NI2]", "TAM[NI3]"
)

missing_vars <- missing_vars[missing_vars %in% names(out)]

item_vars_no_tam <- c(
  "Habit[Habit1]", "Habit[Habit2]", "Habit[Habit3]", "Habit[Habit4]",
  "Intention1[Int1]", "Intention2[Int2]", "Intention3[Int3]",
  "Att1[Att1]", "Att2[Att2]", "Att3[Att3]", "Att4[Att4]", "Att5[Att5]",
  "Norm1[Norm1]", "Norm2[Norm2]", "Norm3[Norm3]",
  "Norm4[Norm4]", "Norm5[Norm5]", "Norm6[Norm6]",
  "Control1[Con1]", "Control2[Con2]", "Control3[Con3]", "Control4[Con4]",
  "KIM[IntVer1]", "KIM[IntVer2]", "KIM[IntVer3]",
  "KIM[wKomp1]", "KIM[wKomp2]", "KIM[wKomp3]",
  "KIM[wWahl1]", "KIM[wWahl2]", "KIM[wWahl3]",
  "KIM[DrAn1]", "KIM[DrAn2]", "KIM[DrAn3]",
  "MotivComp[MotivComp1]", "MotivComp[MotivComp2]", "MotivComp[MotivComp3]", "MotivComp[MotivComp4]",
  "ActionPlan[ActionPlan1]", "ActionPlan[ActionPlan2]", "ActionPlan[ActionPlan3]", "ActionPlan[ActionPlan4]",
  "VolSelf[VolSelf1]", "VolSelf[VolSelf2]", "VolSelf[VolSelf3]",
  "ZiMo[discat1]", "ZiMo[discat2]", "ZiMo[discat3]", "ZiMo[discat4]",
  "ZiMo[fit1]", "ZiMo[fit2]", "ZiMo[fit3]",
  "ZiMo[heal1]", "ZiMo[heal2]", "ZiMo[heal3]",
  "ZiMo[comper1]", "ZiMo[comper2]", "ZiMo[comper3]",
  "ZiMo[aes1]", "ZiMo[aes2]",
  "ZiMo[con1]", "ZiMo[con2]", "ZiMo[con3]", "ZiMo[con4]", "ZiMo[con5]",
  "ZiMo[figapp1]", "ZiMo[figapp2]", "ZiMo[figapp3]"
)

item_vars_no_tam <- item_vars_no_tam[item_vars_no_tam %in% names(out)]

cat("\nMissingness zentrale Items ohne TAM:\n")
cat(round(mean(is.na(out[, item_vars_no_tam])), 3), "\n")

for (v in missing_vars) {
  cat(v, ":", round(mean(is.na(out[[v]])), 3), "\n")
}

# =========================================================
# 12) Ceiling / Floor
# =========================================================
print_section("8. CEILING / FLOOR")

dist_vars <- c(
  "Habit[Habit1]", "Habit[Habit2]", "Habit[Habit3]", "Habit[Habit4]",
  "Intention1[Int1]", "Intention2[Int2]", "Intention3[Int3]",
  "Att1[Att1]", "Att2[Att2]", "Att3[Att3]", "Att4[Att4]", "Att5[Att5]",
  "Norm1[Norm1]", "Norm2[Norm2]", "Norm3[Norm3]",
  "Norm4[Norm4]", "Norm5[Norm5]", "Norm6[Norm6]",
  "Control1[Con1]", "Control2[Con2]", "Control3[Con3]", "Control4[Con4]",
  "KIM[IntVer1]", "KIM[IntVer2]", "KIM[IntVer3]",
  "KIM[wKomp1]", "KIM[wKomp2]", "KIM[wKomp3]",
  "KIM[wWahl1]", "KIM[wWahl2]", "KIM[wWahl3]",
  "KIM[DrAn1]", "KIM[DrAn2]", "KIM[DrAn3]",
  "MotivComp[MotivComp1]", "MotivComp[MotivComp2]", "MotivComp[MotivComp3]", "MotivComp[MotivComp4]",
  "ActionPlan[ActionPlan1]", "ActionPlan[ActionPlan2]", "ActionPlan[ActionPlan3]", "ActionPlan[ActionPlan4]",
  "VolSelf[VolSelf1]", "VolSelf[VolSelf2]", "VolSelf[VolSelf3]",
  "ZiMo[discat1]", "ZiMo[discat2]", "ZiMo[discat3]", "ZiMo[discat4]",
  "ZiMo[fit1]", "ZiMo[fit2]", "ZiMo[fit3]",
  "ZiMo[heal1]", "ZiMo[heal2]", "ZiMo[heal3]",
  "ZiMo[comper1]", "ZiMo[comper2]", "ZiMo[comper3]",
  "ZiMo[aes1]", "ZiMo[aes2]",
  "ZiMo[con1]", "ZiMo[con2]", "ZiMo[con3]", "ZiMo[con4]", "ZiMo[con5]",
  "ZiMo[figapp1]", "ZiMo[figapp2]", "ZiMo[figapp3]",
  "TAM[WA1]", "TAM[WA2]", "TAM[WA3]",
  "TAM[WN1]", "TAM[WN2]", "TAM[WN3]",
  "TAM[WB1]", "TAM[WB2]", "TAM[WB3]",
  "TAM[WF1]", "TAM[WF2]", "TAM[WF3]",
  "TAM[NI1]", "TAM[NI2]", "TAM[NI3]"
)

dist_vars <- dist_vars[dist_vars %in% names(out)]

for (v in dist_vars) {
  check_distribution(v)
}

# =========================================================
# 13) Einfache LMMs
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
# 14) Erweiterte LMMs mit Demografie
# =========================================================
print_section("10. ERWEITERTE LMMs MIT DEMOGRAFIE")

if ("Geb" %in% names(out)) {
  out$age_check <- 2026 - as.numeric(out$Geb)
}

if ("Ges" %in% names(out)) {
  out$female_check <- ifelse(out$Ges == "Weiblich", 1,
                             ifelse(out$Ges == "Männlich", 0, NA))
}

if ("AppUseGeneral" %in% names(out)) {
  out$prior_app_check <- ifelse(out$AppUseGeneral == "Ja", 1,
                                ifelse(out$AppUseGeneral == "Nein", 0, NA))
}

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