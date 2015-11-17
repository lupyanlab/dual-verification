library(dplyr)
library(ggplot2)
library(scales)
library(tidyr)

devtools::load_all("dualverification")
data(dualverification)

subjs <- dualverification %>%
	group_by(subj_id) %>%
	summarize(
		rt = mean(rt, na.rm = TRUE),
		error = mean(is_error, na.rm = TRUE)
	) %>%
	mutate(
		rank_rt = rank(rt),
		rank_error = rank(error, ties = "first")
	)

rank_axis_breaks <- c(1, seq(5, nrow(subjs), by = 5))
scale_x_subj_rank <- scale_x_continuous("Rank", breaks = rank_axis_breaks)
subj_xlim <- c(0.5, nrow(subjs) + 2.5)
subj_theme <- theme_minimal() +
  theme(
    axis.ticks = element_blank(),
    legend.position = "none"
  )

ggplot(subjs, aes(x = rank_rt, y = rt, color = subj_id)) +
  geom_point() +
  geom_text(aes(label = subj_id), hjust = 0, angle = 90, size = 3) +
  scale_x_subj_rank +
  scale_y_continuous("Average RT (ms)") +
  coord_cartesian(xlim = subj_xlim, ylim = c(120, 590)) +
  subj_theme
ggsave("descriptives/subjs-rt.png")

ggplot(subjs, aes(x = rank_error, y = error, color = subj_id)) +
  geom_point() +
	geom_text(aes(label = subj_id), hjust = 0, angle = 90, size = 3) +
  scale_x_subj_rank +
  scale_y_continuous("Error Rate", labels = percent) +
  coord_cartesian(xlim = subj_xlim, ylim = c(0, 0.24)) +
  subj_theme
ggsave("descriptives/subjs-error.png")

subjs_parallel <- subjs %>%
  select(-(rt:error)) %>%
  gather(rank_type, rank_value, -subj_id) %>%
  mutate(rank_type = factor(rank_type, levels = c("rank_error", "rank_rt")))

ggplot(subjs_parallel, aes(x = rank_type, y = rank_value, color = subj_id)) +
  geom_line(aes(group = subj_id)) +
  geom_text(aes(label = subj_id),
            data = filter(subjs_parallel, rank_type == "rank_error"),
            hjust = 1) +
  scale_x_discrete("", labels = c("Error", "RT")) +
  scale_y_continuous("Rank", breaks = rank_axis_breaks) +
  subj_theme
ggsave("descriptives/subjs-parallel.png")

z_score <- function(x) (x - mean(x, na.rm = TRUE))/sd(x, na.rm = TRUE)

subjs_parallel_z <- subjs %>%
  mutate(
    rt_z = z_score(rt), 
    error_z = z_score(error)
  ) %>% 
  select(subj_id, rt_z, error_z) %>%
  gather(measure, z_score, -subj_id) %>%
  mutate(measure = factor(measure, levels = c("error_z", "rt_z")))

ggplot(subjs_parallel_z, aes(x = measure, y = z_score, color = subj_id)) +
  geom_line(aes(group = subj_id)) +
  geom_text(aes(label = subj_id),
            data = filter(subjs_parallel_z, measure == "error_z"),
            hjust = 1) +
  scale_x_discrete("", labels = c("Error", "RT")) +
  scale_y_continuous("z-score") +
  coord_cartesian(ylim = c(-2.7, 2.7)) +
  subj_theme
ggsave("descriptives/subjs-parallel-z.png")
