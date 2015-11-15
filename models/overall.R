library(dplyr)
library(ggplot2)

devtools::load_all("dualverification")
data(dualverification)

# ---- overall-mod
overall_mod <- glmer(is_error ~ feat_c * mask_c + response_c + (1|subj_id),
                     data = dualverification,
                     family = binomial)
tidy(overall_mod, effects = "fixed") %>%
  add_sig_stars

# ---- overall-plot
overall_error <- format_mod_preds(overall_mod)

# hack!
# For some reason, model predictions are not
# hitting the sample means.
overall_error <- dualverification %>%
  group_by(feat_c, mask_c, response_c) %>%
  summarize(mean_error = mean(is_error, na.rm = TRUE)) %>%
  left_join(overall_error, .)

ggplot(dualverification, aes(x = mask_c, y = is_error, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  geom_linerange(aes(y = mean_error, ymin = mean_error-se, ymax = mean_error+se),
                  data = overall_error) +
  facet_grid(feat_label ~ response_label) +
  scale_x_mask +
  scale_y_error +
  scale_fill_featmask +
  base_theme