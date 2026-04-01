library(dplyr)
library(tidyr)
library(MASS)

set.seed(1234)

# =========================================================
# 1) Design
# =========================================================
N <- 200

df <- expand.grid(
  id = 1:N,
  timePoint = c("T1", "T2", "T3"),
  stringsAsFactors = FALSE
) %>%
  as_tibble()

group_df <- tibble(
  id = 1:N,
  studyGroup = sample(c("IG", "CG"), N, replace = TRUE)
)

df <- df %>%
  left_join(group_df, by = "id") %>%
  mutate(
    timePoint = factor(timePoint, levels = c("T1", "T2", "T3")),
    treatment_now =
      (studyGroup == "IG" & timePoint == "T2") |
      (studyGroup == "CG" & timePoint == "T3"),
    carryover_ig =
      (studyGroup == "IG" & timePoint == "T3")
  )

# =========================================================
# 2) Personenebene / Random Intercepts
# =========================================================
# Korrelationen grob entlang der Deep-Research-Pfade
Sigma <- matrix(c(
  1.00, 0.30, 0.25, 0.15, 0.20, 0.35, 0.40, 0.20, 0.15,
  0.30, 1.00, 0.60, 0.32, 0.35, 0.57, 0.40, 0.45, 0.20,
  0.25, 0.60, 1.00, 0.30, 0.30, 0.35, 0.25, 0.20, 0.15,
  0.15, 0.32, 0.30, 1.00, 0.35, 0.20, 0.15, 0.10, 0.10,
  0.20, 0.35, 0.30, 0.35, 1.00, 0.25, 0.20, 0.10, 0.10,
  0.35, 0.57, 0.35, 0.20, 0.25, 1.00, 0.30, 0.30, 0.15,
  0.40, 0.40, 0.25, 0.15, 0.20, 0.30, 1.00, 0.35, 0.10,
  0.20, 0.45, 0.20, 0.10, 0.10, 0.30, 0.35, 1.00, 0.10,
  0.15, 0.20, 0.15, 0.10, 0.10, 0.15, 0.10, 0.10, 1.00
), nrow = 9, byrow = TRUE)

latent_person <- MASS::mvrnorm(
  n = N,
  mu = rep(0, 9),
  Sigma = Sigma
)

colnames(latent_person) <- c(
  "z_habit", "z_intention", "z_attitude", "z_injnorm", "z_descnorm",
  "z_pbc", "z_intrinsic_mot", "z_planning", "z_selfcontrol"
)

latent_person <- as_tibble(latent_person)
latent_person$id <- 1:N

df <- df %>%
  left_join(latent_person, by = "id")

# =========================================================
# 3) Baselineparameter
# =========================================================
habit_mean_t1 <- 2.11
habit_sd_between <- 1.00
habit_sd_within  <- 0.90
habit_effect     <- 0.66
habit_carryover  <- 0.25 * habit_effect

steps_base       <- 3500
steps_effect     <- 500
steps_sd_between <- 2500
steps_sd_within  <- 1800 / sqrt(7)
steps_to_met     <- 0.21

intention_mean <- 5.0
intention_sd   <- 1.2
intention_eff  <- 0.35

attitude_mean  <- 5.2
attitude_sd    <- 1.1
attitude_eff   <- 0.25

injnorm_mean   <- 4.2
injnorm_sd     <- 1.2
injnorm_eff    <- 0.15

descnorm_mean  <- 4.0
descnorm_sd    <- 1.2
descnorm_eff   <- 0.15

pbc_mean       <- 4.8
pbc_sd         <- 1.1
pbc_eff        <- 0.25

intrinsic_mot_mean    <- 3.4
intrinsic_mot_sd      <- 0.7
intrinsic_mot_eff     <- 0.25

perceived_comp_mean   <- 3.1
perceived_comp_sd     <- 0.7
perceived_comp_eff    <- 0.20

perceived_choice_mean <- 3.0
perceived_choice_sd   <- 0.7
perceived_choice_eff  <- 0.15

extrinsic_mot_mean    <- 1.6
extrinsic_mot_sd      <- 0.7
extrinsic_mot_eff     <- 0.05

planning_mean  <- 2.17
planning_sd    <- 0.70
planning_eff   <- 0.30

selfcontrol_mean <- 3.3
selfcontrol_sd   <- 0.7
selfcontrol_eff  <- 0.08

# BMZI
bmzi_fit_mean  <- 4.34; bmzi_fit_sd  <- 0.57
bmzi_body_mean <- 3.15; bmzi_body_sd <- 1.09
bmzi_contact_mean <- 2.60; bmzi_contact_sd <- 1.07
bmzi_comp_mean <- 2.18; bmzi_comp_sd <- 0.89
bmzi_dis_mean  <- 3.04; bmzi_dis_sd  <- 1.00
bmzi_aes_mean  <- 3.26; bmzi_aes_sd  <- 1.23

# Neue ZiMo-Faktoren / zusätzliche Motive
zimo_discat_mean <- 3.28   # Stress reduction
zimo_discat_sd   <- 1.00

zimo_enjoy_mean  <- 3.69   # Activation/Enjoyment
zimo_enjoy_sd    <- 0.88

zimo_risk_mean   <- 2.29   # Competition/Performance Proxy
zimo_risk_sd     <- 1.04

zimo_discat_eff <- 0.10
zimo_enjoy_eff  <- 0.15
zimo_risk_eff   <- 0.05

# TAM
tam_mean <- 5.0
tam_sd   <- 1.0

# =========================================================
# 4) Longitudinale latente Konstrukte
# =========================================================
to_range <- function(x, mean, sd, min_val, max_val) {
  y <- mean + x * sd
  pmin(pmax(y, min_val), max_val)
}

df <- df %>%
  mutate(
    trt = ifelse(treatment_now, 1, 0),
    carry = ifelse(carryover_ig, 1, 0),

    habit_latent =
      habit_mean_t1 +
      z_habit * habit_sd_between +
      trt * habit_effect +
      carry * habit_carryover +
      rnorm(n(), 0, habit_sd_within),

    intention_latent =
      intention_mean +
      z_intention * intention_sd +
      trt * intention_eff +
      carry * (0.2 * intention_eff) +
      rnorm(n(), 0, 0.6),

    attitude_latent =
      attitude_mean +
      z_attitude * attitude_sd +
      trt * attitude_eff +
      rnorm(n(), 0, 0.5),

    injnorm_latent =
      injnorm_mean +
      z_injnorm * injnorm_sd +
      trt * injnorm_eff +
      rnorm(n(), 0, 0.6),

    descnorm_latent =
      descnorm_mean +
      z_descnorm * descnorm_sd +
      trt * descnorm_eff +
      rnorm(n(), 0, 0.6),

    pbc_latent =
      pbc_mean +
      z_pbc * pbc_sd +
      trt * pbc_eff +
      rnorm(n(), 0, 0.5),

    intrinsic_mot_latent =
      intrinsic_mot_mean +
      z_intrinsic_mot * intrinsic_mot_sd +
      trt * intrinsic_mot_eff +
      carry * (0.2 * intrinsic_mot_eff) +
      rnorm(n(), 0, 0.4),

    perceived_comp_latent =
      perceived_comp_mean +
      0.50 * z_intrinsic_mot * perceived_comp_sd +
      trt * perceived_comp_eff +
      carry * (0.2 * perceived_comp_eff) +
      rnorm(n(), 0, 0.4),

    perceived_choice_latent =
      perceived_choice_mean +
      0.40 * z_intrinsic_mot * perceived_choice_sd +
      trt * perceived_choice_eff +
      carry * (0.2 * perceived_choice_eff) +
      rnorm(n(), 0, 0.4),

    extrinsic_mot_latent =
      extrinsic_mot_mean +
      0.20 * z_intrinsic_mot * extrinsic_mot_sd -
      0.10 * trt +
      rnorm(n(), 0, 0.5),

    planning_latent =
      planning_mean +
      z_planning * planning_sd +
      trt * planning_eff +
      rnorm(n(), 0, 0.35),

    selfcontrol_latent =
      selfcontrol_mean +
      z_selfcontrol * selfcontrol_sd +
      trt * selfcontrol_eff +
      rnorm(n(), 0, 0.25),

    zimo_discat_latent =
      zimo_discat_mean +
      0.25 * scale(intrinsic_mot_latent)[,1] +
      0.20 * scale(attitude_latent)[,1] +
      trt * zimo_discat_eff +
      rnorm(n(), 0, 1.00),

    zimo_enjoy_latent =
      zimo_enjoy_mean +
      0.45 * scale(intrinsic_mot_latent)[,1] +
      0.20 * scale(attitude_latent)[,1] +
      trt * zimo_enjoy_eff +
      rnorm(n(), 0, 0.85),

    zimo_risk_latent =
      zimo_risk_mean +
      0.20 * scale(intention_latent)[,1] +
      0.25 * scale(selfcontrol_latent)[,1] +
      trt * zimo_risk_eff +
      rnorm(n(), 0, 1.00)
  )

# =========================================================
# 5) Demografie / soziodemografische Determinanten
# =========================================================
subj_demo <- tibble(
  id = 1:N,
  age = pmin(pmax(round(rnorm(N, 40, 11)), 18), 70),

  # 0 = male, 1 = female
  # Paper: App-Nutzung stärker bei Frauen
  gender = rbinom(N, 1, 0.70),

  # prior app usage
  prior_app = rbinom(N, 1, 0.35),

  # income / SES: 1 = low, 2 = medium, 3 = high
  income = sample(1:3, N, replace = TRUE, prob = c(0.35, 0.40, 0.25))
)

df <- df %>% left_join(subj_demo, by = "id")

# Hilfsvariablen für Simulation
df <- df %>%
  mutate(
    age_c = age - mean(age),

    female = gender,                 # 1 = female
    male   = 1 - gender,

    income_low  = ifelse(income == 1, 1, 0),
    income_med  = ifelse(income == 2, 1, 0),
    income_high = ifelse(income == 3, 1, 0),

    # Altersfenster 25-50 mit höherer App-Nutzungsneigung laut Paper
    age_25_50 = ifelse(age >= 25 & age <= 50, 1, 0)
  )


# =========================================================
# 6) Physical Activity (primary outcome = MET-minutes/week)
# =========================================================

# A. BASELINE INACTIVE PROFILE (Kai / Nigg et al., 2024 logic)
base_vpa_mins_pa <- 0
base_mpa_mins_pa <- 10
base_lpa_mins_pa <- 120

intercept_met_pa <- (9 * base_vpa_mins_pa) + (5 * base_mpa_mins_pa) + (3 * base_lpa_mins_pa)  # 410

# B. INTERVENTION EFFECT
time_met_pa <- 105
carry_met_pa <- round(0.25 * time_met_pa, 2)

# C. COVARIATE ESTIMATES (Kai)
age_met_pa <- -5
gender_met_pa <- 150      # increase for being male
prior_app_met_pa <- 200
high_ses_met_pa <- 150    # here: income_high = 1

# D. VARIANCE PARAMETERS
bp_sd_met_pa <- 310
wp_sd_met_pa <- 250

# person-level random intercept for PA
pa_random_intercept <- tibble(
  id = 1:N,
  rand_pa = rnorm(N, 0, bp_sd_met_pa)
)

df <- df %>%
  left_join(pa_random_intercept, by = "id") %>%
  mutate(
    # small psychological term so PA remains related to key constructs
    pa_driver_small =
      20 * scale(habit_latent)[,1] +
      15 * scale(intention_latent)[,1] +
      10 * scale(pbc_latent)[,1] +
      10 * scale(intrinsic_mot_latent)[,1],

    weeklyMET_minutes =
      intercept_met_pa +
      rand_pa +
      trt * time_met_pa +
      carry * carry_met_pa +
      age_c * age_met_pa +
      male * gender_met_pa +
      prior_app * prior_app_met_pa +
      income_high * high_ses_met_pa +
      pa_driver_small +
      rnorm(n(), 0, wp_sd_met_pa),

    weeklyMET_minutes = pmax(round(weeklyMET_minutes), 0)
  )

# =========================================================
# 7) Derive survey-based PA variables from weekly MET-minutes
# =========================================================

df <- df %>%
  mutate(
    # low-activity composition:
    # LPA dominant, MPA smaller, VPA usually minimal
    df <- df %>%
      mutate(
        treat_phase_pa = ifelse(trt == 1 | carry == 1, 1, 0),

        vpa_share = ifelse(weeklyMET_minutes < 650, 0, runif(n(), 0.00, 0.03)),

        mpa_share = ifelse(
          treat_phase_pa == 1,
          runif(n(), 0.22, 0.32),
          runif(n(), 0.16, 0.24)
        ),

        lpa_share = pmax(1 - vpa_share - mpa_share, 0.68),

        share_sum = lpa_share + mpa_share + vpa_share,
        lpa_share = lpa_share / share_sum,
        mpa_share = mpa_share / share_sum,
        vpa_share = vpa_share / share_sum,

        lpa_met_week = weeklyMET_minutes * lpa_share,
        mpa_met_week = weeklyMET_minutes * mpa_share,
        vpa_met_week = weeklyMET_minutes * vpa_share,

        lpa_min_week = lpa_met_week / 3,
        mpa_min_week = mpa_met_week / 5,
        vpa_min_week = vpa_met_week / 9
      )
    )

make_days_from_minutes <- function(min_week, target_min_per_day) {
  days <- ifelse(min_week <= 0, 0, round(min_week / target_min_per_day))
  days <- pmin(pmax(days, 0), 7)
  days
}

safe_minutes_per_day <- function(min_week, days) {
  ifelse(days > 0, pmax(round(min_week / days), 5), NA)
}

df <- df %>%
  mutate(
    pa_light_days = make_days_from_minutes(lpa_min_week, 35),
    pa_mod_days   = make_days_from_minutes(mpa_min_week, 25),
    pa_vig_days   = make_days_from_minutes(vpa_min_week, 20),

    pa_light_minutes = safe_minutes_per_day(lpa_min_week, pa_light_days),
    pa_mod_minutes   = safe_minutes_per_day(mpa_min_week, pa_mod_days),
    pa_vig_minutes   = safe_minutes_per_day(vpa_min_week, pa_vig_days),

    pa_light_minutes = ifelse(pa_light_days == 0, NA, pa_light_minutes),
    pa_mod_minutes   = ifelse(pa_mod_days == 0, NA, pa_mod_minutes),
    pa_vig_minutes   = ifelse(pa_vig_days == 0, NA, pa_vig_minutes),

    weeklyMET_minutes_check =
      ifelse(is.na(pa_vig_days), 0, pa_vig_days) * ifelse(is.na(pa_vig_minutes), 0, pa_vig_minutes) * 9 +
      ifelse(is.na(pa_mod_days), 0, pa_mod_days) * ifelse(is.na(pa_mod_minutes), 0, pa_mod_minutes) * 5 +
      ifelse(is.na(pa_light_days), 0, pa_light_days) * ifelse(is.na(pa_light_minutes), 0, pa_light_minutes) * 3
  )

# =========================================================
# 8) Steps/day only for AI-app phases (kept in CSV, not mapped to survey export)
# =========================================================

base_steps_day_pa <- 3500
sesoi_steps_day_pa <- 500

age_steps_year_pa <- -15
gender_steps_male_pa <- 400
prior_app_steps_pa <- 800
high_ses_steps_pa <- 500

bp_sd_steps_pa <- 2500
wp_sd_steps_1day_pa <- 1800
n_days_agg_pa <- 7

valid_steps_phase <- (df$studyGroup == "IG" & df$timePoint == "T2") |
                     (df$studyGroup == "CG" & df$timePoint == "T3")

steps_random_intercept <- tibble(
  id = 1:N,
  rand_steps = rnorm(N, 0, bp_sd_steps_pa)
)

df <- df %>%
  left_join(steps_random_intercept, by = "id") %>%
  mutate(
    steps_day = ifelse(
      valid_steps_phase,
      base_steps_day_pa +
        rand_steps +
        trt * sesoi_steps_day_pa +
        carry * (0.25 * sesoi_steps_day_pa) +
        age_c * age_steps_year_pa +
        male * gender_steps_male_pa +
        prior_app * prior_app_steps_pa +
        income_high * high_ses_steps_pa +
        rnorm(n(), 0, wp_sd_steps_1day_pa / sqrt(n_days_agg_pa)),
      NA
    ),

    steps_day = ifelse(!is.na(steps_day), pmax(round(steps_day), 0), NA)
  )
  
# =========================================================
# 9) Itemgeneratoren
# =========================================================
likert_1_5 <- function(x) pmin(pmax(round(x), 1), 5)
likert_1_7 <- function(x) pmin(pmax(round(x), 1), 7)
likert_1_4 <- function(x) pmin(pmax(round(x), 1), 4)

# Habit 1-5
df <- df %>%
  mutate(
    habit_1 = likert_1_5(habit_latent + rnorm(n(), 0, 0.6)),
    habit_2 = likert_1_5(habit_latent + rnorm(n(), 0, 0.6)),
    habit_3 = likert_1_5(habit_latent + rnorm(n(), 0, 0.6)),
    habit_4 = likert_1_5(habit_latent + rnorm(n(), 0, 0.6))
  )

# TPB 1-7
df <- df %>%
  mutate(
    intention_1 = likert_1_7(intention_latent + rnorm(n(), 0, 0.7)),
    intention_2 = likert_1_7(intention_latent + rnorm(n(), 0, 0.7)),
    intention_3 = likert_1_7(intention_latent + rnorm(n(), 0, 0.7)),

    attitude_1 = likert_1_7(attitude_latent + rnorm(n(), 0, 0.7)),
    attitude_2 = likert_1_7(attitude_latent + rnorm(n(), 0, 0.7)),
    attitude_3 = likert_1_7(attitude_latent + rnorm(n(), 0, 0.7)),
    attitude_4 = likert_1_7(attitude_latent + rnorm(n(), 0, 0.7)),
    attitude_5 = likert_1_7(attitude_latent + rnorm(n(), 0, 0.7)),

    norm_inj_1 = likert_1_7(injnorm_latent + rnorm(n(), 0, 0.8)),
    norm_inj_2 = likert_1_7(injnorm_latent + rnorm(n(), 0, 0.8)),
    norm_inj_3 = likert_1_7(injnorm_latent + rnorm(n(), 0, 0.8)),

    norm_desc_1 = likert_1_7(descnorm_latent + rnorm(n(), 0, 0.8)),
    norm_desc_2 = likert_1_7(descnorm_latent + rnorm(n(), 0, 0.8)),
    norm_desc_3 = likert_1_7(descnorm_latent + rnorm(n(), 0, 0.8)),

    pbc_1 = likert_1_7(pbc_latent + rnorm(n(), 0, 0.7)),
    pbc_2 = likert_1_7(pbc_latent + rnorm(n(), 0, 0.7)),
    pbc_3 = likert_1_7(pbc_latent + rnorm(n(), 0, 0.7)),
    pbc_4 = likert_1_7(pbc_latent + rnorm(n(), 0, 0.7))
  )

# SDT 0-4
likert_0_4 <- function(x) pmin(pmax(round(x), 0), 4)

df <- df %>%
  mutate(
    intrinsic_mot_1 = likert_0_4(intrinsic_mot_latent + rnorm(n(), 0, 0.5)),
    intrinsic_mot_2 = likert_0_4(intrinsic_mot_latent + rnorm(n(), 0, 0.5)),
    intrinsic_mot_3 = likert_0_4(intrinsic_mot_latent + rnorm(n(), 0, 0.5)),

    perceived_comp_1 = likert_0_4(perceived_comp_latent + rnorm(n(), 0, 0.5)),
    perceived_comp_2 = likert_0_4(perceived_comp_latent + rnorm(n(), 0, 0.5)),
    perceived_comp_3 = likert_0_4(perceived_comp_latent + rnorm(n(), 0, 0.5)),

    perceived_choice_1 = likert_0_4(perceived_choice_latent + rnorm(n(), 0, 0.5)),
    perceived_choice_2 = likert_0_4(perceived_choice_latent + rnorm(n(), 0, 0.5)),
    perceived_choice_3 = likert_0_4(perceived_choice_latent + rnorm(n(), 0, 0.5)),

    extrinsic_mot_1 = likert_0_4(extrinsic_mot_latent + rnorm(n(), 0, 0.6)),
    extrinsic_mot_2 = likert_0_4(extrinsic_mot_latent + rnorm(n(), 0, 0.6)),
    extrinsic_mot_3 = likert_0_4(extrinsic_mot_latent + rnorm(n(), 0, 0.6))
  )

# Planning 1-4
df <- df %>%
  mutate(
    action_planning_1 = likert_1_4(planning_latent + rnorm(n(), 0, 0.4)),
    action_planning_2 = likert_1_4(planning_latent + rnorm(n(), 0, 0.4)),
    action_planning_3 = likert_1_4(planning_latent + rnorm(n(), 0, 0.4)),
    action_planning_4 = likert_1_4(planning_latent + rnorm(n(), 0, 0.4))
  )

# Self-control 1-5
df <- df %>%
  mutate(
    self_control_1 = likert_1_5(selfcontrol_latent + rnorm(n(), 0, 0.5)),
    self_control_2 = likert_1_5(selfcontrol_latent + rnorm(n(), 0, 0.5)),
    self_control_3 = likert_1_5(selfcontrol_latent + rnorm(n(), 0, 0.5))
  )

# Motivationale Kompetenz 1-5
df <- df %>%
  mutate(
    motivational_comp_1 = likert_1_5(3.2 + 0.3 * scale(intrinsic_mot_latent)[,1] + rnorm(n(), 0, 0.5)),
    motivational_comp_2 = likert_1_5(3.2 + 0.3 * scale(intrinsic_mot_latent)[,1] + rnorm(n(), 0, 0.5)),
    motivational_comp_3 = likert_1_5(3.2 + 0.3 * scale(intrinsic_mot_latent)[,1] + rnorm(n(), 0, 0.5)),
    motivational_comp_4 = likert_1_5(3.2 + 0.3 * scale(intrinsic_mot_latent)[,1] + rnorm(n(), 0, 0.5))
  )

# BMZI 1-5
df <- df %>%
  mutate(
    bmzi_fitness     = likert_1_5(rnorm(n(), bmzi_fit_mean, bmzi_fit_sd)),
    bmzi_health      = likert_1_5(rnorm(n(), bmzi_fit_mean, bmzi_fit_sd)),
    bmzi_body        = likert_1_5(rnorm(n(), bmzi_body_mean, bmzi_body_sd)),
    bmzi_social      = likert_1_5(rnorm(n(), bmzi_contact_mean, bmzi_contact_sd)),
    bmzi_competition = likert_1_5(rnorm(n(), bmzi_comp_mean, bmzi_comp_sd)),
    bmzi_distraction = likert_1_5(rnorm(n(), bmzi_dis_mean, bmzi_dis_sd)),
    bmzi_aesthetics  = likert_1_5(rnorm(n(), bmzi_aes_mean, bmzi_aes_sd)),
    zimo_discat5 = likert_1_5(zimo_discat_latent + rnorm(n(), 0, 0.45)),
    zimo_enjoy1 = likert_1_5(zimo_enjoy_latent + rnorm(n(), 0, 0.60)),
    zimo_enjoy2 = likert_1_5(zimo_enjoy_latent + rnorm(n(), 0, 0.60)),
    zimo_enjoy3 = likert_1_5(zimo_enjoy_latent + rnorm(n(), 0, 0.60)),
    zimo_risk1 = likert_1_5(zimo_risk_latent + rnorm(n(), 0, 0.60)),
    zimo_risk2 = likert_1_5(zimo_risk_latent + rnorm(n(), 0, 0.60)),
    zimo_risk3 = likert_1_5(zimo_risk_latent + rnorm(n(), 0, 0.65))
  )

# =========================================================
# 10) TAM nur in Interventionsphasen
# =========================================================
valid_tam <- (df$studyGroup == "IG" & df$timePoint == "T2") |
             (df$studyGroup == "CG" & df$timePoint == "T3")

tam_latent <- tam_mean + 0.5 * as.numeric(df$treatment_now) + rnorm(nrow(df), 0, tam_sd)

df <- df %>%
  mutate(
    # In der Bewertungsphase hat jede Person prinzipiell TAM-Daten
    app_use_prob = plogis(
      -0.4 +
        0.55 * female +        # Frauen höhere App-Nutzung
        0.45 * age_25_50 +     # 25-50 günstiger
        0.35 * prior_app +     # Vorerfahrung positiv
        -0.30 * income_high +  # niedrigere SES eher höhere App-Nutzung
        0.15 * trt
    ),

    app_use_yesno = ifelse(valid_tam, rbinom(n(), 1, app_use_prob), 0),

    app_use_days = ifelse(
      valid_tam & app_use_yesno == 1,
      pmin(
        7,
        pmax(
          1,
          round(rnorm(
            n(),
            mean = 3.8 +
              1.8 * female +
              2.0 * age_25_50 +
              1.0 * prior_app -
              1.2 * income_high,
            sd = 1.3
          ))
        )
      ),
      NA
    ),

    tam_usefulness_1 = ifelse(valid_tam, likert_1_7(tam_latent + rnorm(n(), 0, 0.6)), NA),
    tam_usefulness_2 = ifelse(valid_tam, likert_1_7(tam_latent + rnorm(n(), 0, 0.6)), NA),
    tam_usefulness_3 = ifelse(valid_tam, likert_1_7(tam_latent + rnorm(n(), 0, 0.6)), NA),

    tam_ease_1 = ifelse(valid_tam, likert_1_7(4.8 + rnorm(n(), 0, 0.8)), NA),
    tam_ease_2 = ifelse(valid_tam, likert_1_7(4.8 + rnorm(n(), 0, 0.8)), NA),
    tam_ease_3 = ifelse(valid_tam, likert_1_7(4.8 + rnorm(n(), 0, 0.8)), NA),

    tam_enjoyment_1 = ifelse(valid_tam, likert_1_7(4.7 + rnorm(n(), 0, 0.9)), NA),
    tam_enjoyment_2 = ifelse(valid_tam, likert_1_7(4.7 + rnorm(n(), 0, 0.9)), NA),
    tam_enjoyment_3 = ifelse(valid_tam, likert_1_7(4.7 + rnorm(n(), 0, 0.9)), NA),

    tam_trust_1 = ifelse(valid_tam, likert_1_7(4.8 + rnorm(n(), 0, 0.9)), NA),
    tam_trust_2 = ifelse(valid_tam, likert_1_7(4.8 + rnorm(n(), 0, 0.9)), NA),
    tam_trust_3 = ifelse(valid_tam, likert_1_7(4.8 + rnorm(n(), 0, 0.9)), NA),

    tam_future_use_1 = ifelse(valid_tam, likert_1_7(5.0 + rnorm(n(), 0, 0.9)), NA),
    tam_future_use_2 = ifelse(valid_tam, likert_1_7(5.0 + rnorm(n(), 0, 0.9)), NA),
    tam_future_use_3 = ifelse(valid_tam, likert_1_7(5.0 + rnorm(n(), 0, 0.9)), NA)
  )


# =========================================================
# 11) Missingness / Dropout
# =========================================================
drop_ids_t2 <- sample(1:N, size = round(0.10 * N))
drop_ids_t3_extra <- sample(setdiff(1:N, drop_ids_t2), size = round(0.10 * N))

item_cols <- grep(
  "^(habit_|intention_|attitude_|norm_|pbc_|intrinsic_mot_|perceived_comp_|perceived_choice_|extrinsic_mot_|action_planning_|self_control_|motivational_comp_|tam_|bmzi_)",
  names(df), value = TRUE
)

# monotones Dropout
df[df$id %in% drop_ids_t2 & df$timePoint %in% c("T2", "T3"), item_cols] <- NA
df[df$id %in% drop_ids_t2 & df$timePoint %in% c("T2", "T3"),
   c("weeklyMET_minutes","pa_vig_days","pa_vig_minutes","pa_mod_days","pa_mod_minutes","pa_light_days","pa_light_minutes")] <- NA

df[df$id %in% drop_ids_t3_extra & df$timePoint == "T3", item_cols] <- NA
df[df$id %in% drop_ids_t3_extra & df$timePoint == "T3",
   c("weeklyMET_minutes","pa_vig_days","pa_vig_minutes","pa_mod_days","pa_mod_minutes","pa_light_days","pa_light_minutes")] <- NA

# kleines MCAR
for (cl in item_cols) {
  miss <- sample(seq_len(nrow(df)), size = round(0.05 * nrow(df)))
  df[[cl]][miss] <- NA
}

# =========================================================
# 11) Export
# =========================================================
write.csv(
  df,
  "C:/Users/rre00/OneDrive - Universitaet Bern/Universität/Master/FS_26/Masterarbeit/Anstellung/Data_Simulation/AIcoPA_simulation_v3_itemdata.csv",
  row.names = FALSE
)

cat("Simulation V3 erstellt: AIcoPA_simulation_v3_itemdata.csv\n")