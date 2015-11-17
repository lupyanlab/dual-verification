library(dplyr)
library(ggplot2)
library(lme4)
library(broom)

devtools::load_all("dualverification")
data(dualverification)
data(proposition_ratings)

dualverification <- left_join(dualverification, proposition_ratings)

# ---- amount-visual-mod
amount_visual_mod <- glmer(is_error ~ feat_c * imagery_mean + (1|subj_id),
                           data = filter(dualverification, response_type == "prompt"),
                           family = binomial)
tidy(amount_visual_mod, effects = "fixed") %>%
  add_sig_stars

# ---- amount-nonvisual-mod
amount_nonvisual_mod <- glmer(is_error ~ feat_c * facts_mean + (1|subj_id),
                              data = filter(dualverification, response_type == "prompt"),
                              family = binomial)
tidy(amount_nonvisual_mod, effects = "fixed") %>%
  add_sig_stars
