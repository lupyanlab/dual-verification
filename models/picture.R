library(dplyr)
library(ggplot2)
library(lme4)
library(broom)

devtools::load_all("dualverification")
data(dualverification)

# ---- pic-mod
pic_mod <- glmer(is_error ~ feat_c * mask_c + (feat_c * mask_c|subj_id),
                 data = filter(dualverification, response_type == "pic"),
                 family = binomial)
tidy(pic_mod, effects = "fixed") %>%
  add_sig_stars

# ---- pic-plot
pred_error <- format_mod_preds(pic_mod)

ggplot(filter(dualverification, response_type == "pic"),
       aes(x = mask_c, y = is_error, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  geom_pointrange(aes(y = estimate, ymin = estimate-se, ymax = estimate+se),
                  data = pred_error) +
  facet_wrap("feat_label") +
  scale_x_mask +
  scale_y_error +
  scale_fill_featmask +
  base_theme +
  ggtitle("Verify picture")
