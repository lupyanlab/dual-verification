#' Tidy up the model predictions for plotting.
#'
#' X predictions are all unique combinations of
#' feat_type (visual, nonvisual), mask_type (nomask, mask),
#' and response_type (pic, prompt). Character combinations
#' are sent to the recode function in this package.
#'
#' @importFrom dplyr `%>%`
#' @param mod Model (lmer, glmer) to pass to predict function.
#' @return a tidy data frame containing all x predictors and y predictions.
#' @export
format_mod_preds <- function(mod) {
  x_preds <- expand.grid(
    feat_type = c("visual", "nonvisual"),
    mask_type = c("mask", "nomask"),
    response_type = c("pic", "prompt"),
    stringsAsFactors = FALSE
  ) %>% recode
  y_preds <- AICcmodavg::predictSE(mod, x_preds, se = TRUE, print.matrix = TRUE)
  preds <- cbind(x_preds, y_preds) %>%
    dplyr::rename(estimate = fit, se = se.fit) %>%
    drop_duplicates
  preds
}

drop_duplicates <- function(frame) {
  # TODO: remove unused columns (those with 1 value only)
  frame[!duplicated(frame$estimate), ]
}
