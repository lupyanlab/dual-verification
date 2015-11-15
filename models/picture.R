library(dplyr)
library(ggplot2)
library(lme4)
library(broom)

devtools::load_all("dualverification")
data(dualverification)

# ---- pic-mod
pic_mod <- glmer(is_error ~ feat_c * mask_c + (1|subj_id),
                 data = filter(dualverification, response_type == "pic"),
                 family = binomial)
tidy(pic_mod, effects = "fixed") %>%
  add_sig_stars

# ---- pic-plot
pred_error <- format_mod_preds(pic_mod)

# hack!
# For some reason, model predictions are not
# hitting the sample means.
pred_error <- dualverification %>%
  filter(response_type == "pic") %>%
  group_by(feat_c, mask_c) %>%
  summarize(mean_error = mean(is_error, na.rm = TRUE)) %>%
  left_join(pred_error, .)

ggplot(filter(dualverification, response_type == "pic"),
       aes(x = mask_c, y = is_error, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  geom_linerange(aes(y = mean_error, ymin = mean_error-se, ymax = mean_error+se),
                  data = pred_error) +
  facet_wrap("feat_label") +
  scale_x_mask +
  scale_y_error +
  scale_fill_featmask +
  base_theme +
  ggtitle("Verify picture")
