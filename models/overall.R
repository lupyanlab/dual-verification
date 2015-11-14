library(ggplot2)

devtools::load_all("dualverification")
# data(dualverification)
# experiment in progress, load from source:
dualverification <- compile("experiment/data/") %>%
  clean %>% 
  recode %>%
  # Combine feat_type and mask_type for colors in the plot
  mutate(feat_mask = paste(feat_type, mask_type, sep = ":"))

# ---- overall-plot
ggplot(dualverification, aes(x = mask_c, y = is_error, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  facet_grid(feat_label ~ response_label) +
  scale_x_mask +
  scale_y_error +
  scale_fill_featmask +
  base_theme