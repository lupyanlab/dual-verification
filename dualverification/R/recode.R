#' Recode all of the factors in the experiment.
#' 
#' @param frame A data.frame with columns: feat_type, mask_type, response_type
#' @importFrom dplyr `%>%`
#' @export
recode <- function(frame) {
  frame %>% 
    recode_feat_type %>%
    recode_mask_type %>%
    recode_response_type
}

recode_feat_type <- function(frame) {
  feat_type_map <- dplyr::data_frame(
    feat_type = c("nonvisual", "visual"),
    feat_c = c(-0.5, 0.5)
  )
  dplyr::left_join(frame, feat_type_map)
}

recode_mask_type <- function(frame) {
  mask_type_map <- dplyr::data_frame(
    mask_type = c("nomask", "mask"),
    mask_c = c(-0.5, 0.5)
  )
  dplyr::left_join(frame, mask_type_map) 
}

recode_response_type <- function(frame) {
  response_type_map <- dplyr::data_frame(
    response_type = c("prompt", "pic"),
    response_label = c("Answer proposition", "Verify picture")
  )
  dplyr::left_join(frame, response_type_map)
}

