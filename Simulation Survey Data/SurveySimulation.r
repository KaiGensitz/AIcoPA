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
  "z_pbc", "z_auto_mot", "z_planning", "z_selfcontrol"
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

auto_mot_mean  <- 3.8
auto_mot_sd    <- 0.8
auto_mot_eff   <- 0.30

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

    auto_mot_latent =
      auto_mot_mean +
      z_auto_mot * auto_mot_sd +
      trt * auto_mot_eff +
      carry * (0.2 * auto_mot_eff) +
      rnorm(n(), 0, 0.4),

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
      0.25 * scale(auto_mot_latent)[,1] +
      0.20 * scale(attitude_latent)[,1] +
      trt * zimo_discat_eff +
      rnorm(n(), 0, 1.00),

    zimo_enjoy_latent =
      zimo_enjoy_mean +
      0.45 * scale(auto_mot_latent)[,1] +
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
# 6) PA
# =========================================================
df <- df %>%
  mutate(
    pa_driver =
      0.35 * scale(habit_latent)[,1] +
      0.30 * scale(intention_latent)[,1] +
      0.20 * scale(pbc_latent)[,1] +
      0.15 * scale(auto_mot_latent)[,1],

    # Paper-informierte soziodemografische Einflüsse:
    # - Männer eher höhere guideline-nahe PA
    # - prior app use positiv
    # - höheres income leicht positiv auf PA
    # - Alter leicht kurvilinear / mittlere Altersgruppen günstiger
    pa_demo_effect =
      (-320) * female +
      180 * prior_app +
      120 * income_high +
       40 * income_med +
       220 * age_25_50 +
       12 * age_c,

    steps_day =
      steps_base +
      z_habit * steps_sd_between +
      trt * steps_effect +
      carry * (0.25 * steps_effect) +
      pa_driver * 350 +
      pa_demo_effect +
      rnorm(n(), 0, steps_sd_within),

    steps_day = pmax(steps_day, 0),
    weeklyMET_minutes = round(steps_day * steps_to_met)
  )

# =========================================================
# 7) Survey-PA als days/minutes -- KORRIGIERT
# =========================================================

# Stärkerer Verhaltenstreiber mit explizitem Interventionseffekt
# Stärkerer Verhaltenstreiber mit explizitem Interventionseffekt
df <- df %>%
  mutate(
    pa_prop =
      0.45 * scale(habit_latent)[,1] +
      0.30 * scale(intention_latent)[,1] +
      0.20 * scale(pbc_latent)[,1] +
      0.15 * scale(auto_mot_latent)[,1] +
      0.55 * trt +
      0.20 * carry +

      # soziodemografische Effekte
      (-0.18) * female +
       0.20 * prior_app +
       0.12 * income_high +
       0.05 * income_med +
       0.08 * age_25_50 +
       0.03 * scale(age_c)[,1] +

      rnorm(n(), 0, 0.7)
  )

make_days <- function(x, shift = 0) {
  p <- plogis(x + shift)
  rbinom(length(x), 7, pmin(pmax(p, 0.02), 0.98))
}

# Mehr moderate Aktivität als vigorous, light am häufigsten
df <- df %>%
  mutate(
    pa_vig_days   = make_days(pa_prop, -1.10),
    pa_mod_days   = make_days(pa_prop, -0.15),
    pa_light_days = make_days(pa_prop,  0.55)
  )

# Minuten ebenfalls interventionssensitiv machen
df <- df %>%
  mutate(
    # Frauen: laut Paper eher längere Aktivitätsdauern
    # Männer: eher höhere guideline-Erreichung insgesamt
    vig_mu = log(pmax(5,
      28 + 10 * trt + 4 * carry +
      4 * scale(habit_latent)[,1] +
      3 * male + 2 * prior_app + 2 * income_high
    )),

    mod_mu = log(pmax(5,
      38 + 12 * trt + 5 * carry +
      5 * scale(intention_latent)[,1] +
      3 * female + 3 * prior_app + 2 * age_25_50
    )),

    light_mu = log(pmax(5,
      50 + 8 * trt + 3 * carry +
      3 * scale(auto_mot_latent)[,1] +
      5 * female + 2 * prior_app
    )),

    pa_vig_minutes = ifelse(
      pa_vig_days > 0,
      round(rlnorm(n(), meanlog = vig_mu, sdlog = 0.30)),
      NA
    ),

    pa_mod_minutes = ifelse(
      pa_mod_days > 0,
      round(rlnorm(n(), meanlog = mod_mu, sdlog = 0.28)),
      NA
    ),

    pa_light_minutes = ifelse(
      pa_light_days > 0,
      round(rlnorm(n(), meanlog = light_mu, sdlog = 0.25)),
      NA
    )
  )

# Sicherheit: wenn 0 Tage, dann Minuten = NA
df <- df %>%
  mutate(
    pa_vig_minutes   = ifelse(pa_vig_days == 0, NA, pa_vig_minutes),
    pa_mod_minutes   = ifelse(pa_mod_days == 0, NA, pa_mod_minutes),
    pa_light_minutes = ifelse(pa_light_days == 0, NA, pa_light_minutes)
  )

# Aggregierter PA-Outcome aus Surveydaten
df <- df %>%
  mutate(
    weeklyMET_minutes =
      ifelse(is.na(pa_vig_days), 0, pa_vig_days) * ifelse(is.na(pa_vig_minutes), 0, pa_vig_minutes) * 8 +
      ifelse(is.na(pa_mod_days), 0, pa_mod_days) * ifelse(is.na(pa_mod_minutes), 0, pa_mod_minutes) * 4 +
      ifelse(is.na(pa_light_days), 0, pa_light_days) * ifelse(is.na(pa_light_minutes), 0, pa_light_minutes) * 2
  )
  
# =========================================================
# 8) Itemgeneratoren
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
    autonomous_mot_1 = likert_0_4(auto_mot_latent + rnorm(n(), 0, 0.5)),
    autonomous_mot_2 = likert_0_4(auto_mot_latent + rnorm(n(), 0, 0.5)),
    autonomous_mot_3 = likert_0_4(auto_mot_latent + rnorm(n(), 0, 0.5)),
    autonomous_mot_4 = likert_0_4(auto_mot_latent + rnorm(n(), 0, 0.5)),

    controlled_mot_1 = likert_0_4(1.8 + rnorm(n(), 0, 0.7)),
    controlled_mot_2 = likert_0_4(1.8 + rnorm(n(), 0, 0.7)),
    controlled_mot_3 = likert_0_4(1.8 + rnorm(n(), 0, 0.7)),
    controlled_mot_4 = likert_0_4(1.8 + rnorm(n(), 0, 0.7))
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
    motivational_comp_1 = likert_1_5(3.2 + 0.3 * scale(auto_mot_latent)[,1] + rnorm(n(), 0, 0.5)),
    motivational_comp_2 = likert_1_5(3.2 + 0.3 * scale(auto_mot_latent)[,1] + rnorm(n(), 0, 0.5)),
    motivational_comp_3 = likert_1_5(3.2 + 0.3 * scale(auto_mot_latent)[,1] + rnorm(n(), 0, 0.5)),
    motivational_comp_4 = likert_1_5(3.2 + 0.3 * scale(auto_mot_latent)[,1] + rnorm(n(), 0, 0.5))
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
# 9) TAM nur in Interventionsphasen
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
# 10) Missingness / Dropout
# =========================================================
drop_ids_t2 <- sample(1:N, size = round(0.10 * N))
drop_ids_t3_extra <- sample(setdiff(1:N, drop_ids_t2), size = round(0.10 * N))

item_cols <- grep(
  "^(habit_|intention_|attitude_|norm_|pbc_|autonomous_mot_|controlled_mot_|action_planning_|self_control_|motivational_comp_|tam_|bmzi_|zimo_)",
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
  "C:/Users/rre00/OneDrive - Universitaet Bern/Universität/Master/FS_26/Masterarbeit/Anstellung/Data_Simulation/AIcoPA_simulation_v2_5_itemdata.csv",
  row.names = FALSE
)

cat("Simulation V2.5 erstellt: AIcoPA_simulation_v2_5_itemdata.csv\n")