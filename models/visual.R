library(dplyr)
library(ggplot2)
library(lme4)
library(broom)

devtools::load_all("dualverification")
data(dualverification)

# ---- visual-mod
visual_mod <- glmer(is_error ~ mask_c * response_c + (1|subj_id),
                    data = filter(dualverification, feat_type == "visual"),
                    family = binomial)
tidy(visual_mod, effect = "fixed") %>%
  add_sig_stars

# ---- visual-plot
pred_error <- format_mod_preds(visual_mod)

# hack!
# For some reason, model predictions are not
# hitting the sample means.
pred_error <- dualverification %>%
  filter(feat_type == "visual") %>%
  group_by(mask_c, response_c) %>%
  summarize(mean_error = mean(is_error, na.rm = TRUE)) %>%
  left_join(pred_error, .)

ggplot(filter(dualverification, feat_type == "visual"),
       aes(x = mask_c, y = is_error, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  geom_linerange(aes(y = mean_error, ymin = mean_error-se, ymax = mean_error+se),
                 data = pred_error) +
  facet_wrap("response_label") +
  scale_x_mask +
  scale_y_error +
  scale_fill_featmask +
  base_theme +
  ggtitle("Visual knowledge")
