library(dplyr)
library(ggplot2)
library(lme4)
library(broom)

devtools::load_all("dualverification")
data(dualverification)

# ---- proposition-mod
prompt_mod <- glmer(is_error ~ feat_c * mask_c + (1|subj_id),
                    data = filter(dualverification, response_type == "prompt"),
                    family = binomial)
tidy(prompt_mod, effect = "fixed") %>%
  add_sig_stars

# ---- proposition-plot
pred_error <- format_mod_preds(prompt_mod)

# hack!
# For some reason, model predictions are not
# hitting the sample means.
pred_error <- dualverification %>%
  filter(response_type == "prompt") %>%
  group_by(feat_c, mask_c) %>%
  summarize(mean_error = mean(is_error, na.rm = TRUE)) %>%
  left_join(pred_error, .)
  
ggplot(filter(dualverification, response_type == "prompt"),
       aes(x = mask_c, y = is_error, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  geom_linerange(aes(y = mean_error, ymin = mean_error-se, ymax = mean_error+se),
                 data = pred_error) +
  facet_wrap("feat_label") +
  scale_x_mask +
  scale_y_error +
  scale_fill_featmask +
  base_theme +
  ggtitle("Answer proposition")

# ---- true-proposition-mod
prompt_true_mod <- glmer(is_error ~ feat_c * mask_c + (1|subj_id),
                         data = filter(dualverification,
                                       response_type == "prompt",
                                       correct_response == "yes"),
                         family = binomial)
tidy(prompt_true_mod, effect = "fixed") %>%
  add_sig_stars

# ---- true-proposition-plot
pred_error <- format_mod_preds(prompt_true_mod)

# hack!
# For some reason, model predictions are not
# hitting the sample means.
pred_error <- dualverification %>%
  filter(response_type == "prompt", correct_response == "yes") %>%
  group_by(feat_c, mask_c) %>%
  summarize(mean_error = mean(is_error, na.rm = TRUE)) %>%
  left_join(pred_error, .)

ggplot(filter(dualverification, response_type == "prompt", correct_response == "yes"),
       aes(x = mask_c, y = is_error, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  geom_linerange(aes(y = mean_error, ymin = mean_error-se, ymax = mean_error+se),
                 data = pred_error) +
  facet_wrap("feat_label") +
  scale_x_mask +
  scale_y_error +
  scale_fill_featmask +
  base_theme +
  ggtitle("Answer true proposition")