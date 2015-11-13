library(dplyr)
library(ggplot2)

devtools::load_all("dualverification")
# data(dualverification)
# experiment in progress, load from source:
dualverification <- compile("experiment/data/") %>%
  clean %>% 
  recode

# ---- overall-mod
overall_mod <- glmer(is_error ~ feat_c * mask_c + response_c + (1|subj_id),
                     data = dualverification,
                     family = binomial)
tidy(overall_mod, effects = "fixed") %>%
  add_sig_stars

# ---- overall-plot
overall_error <- format_mod_preds(overall_mod)

ggplot(dualverification, aes(x = mask_c, y = is_error, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  geom_pointrange(aes(y = estimate, ymin = estimate-se, ymax = estimate+se),
                  data = overall_error) +
  facet_grid(feat_label ~ response_label) +
  scale_x_mask +
  scale_y_error +
  scale_fill_featmask +
  base_theme