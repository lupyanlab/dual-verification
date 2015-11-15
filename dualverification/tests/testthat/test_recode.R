library(testthat)
library(dplyr)

devtools::load_all()

context("Recoding variables")

test_that("recode base case", {
  frame <- expand.grid(
    mask_type = c("nomask", "mask"),
    feat_type = c("visual", "nonvisual"),
    response_type = c("pic", "prompt"),
    stringsAsFactors = FALSE
  )

  recoded <- recode(frame)

  expect_equal(nrow(recoded), nrow(frame))
  expect_false(any(duplicated(recoded)))
})

test_that("recode reverse", {
  frame <- expand.grid(
    mask_c = c(-0.5, 0.5),
    feat_c = c(-0.5, 0.5),
    response_c = c(-0.5, 0.5)
  )

  recoded <- recode(frame)

  expect_equal(nrow(recoded), nrow(frame))
  expect_false(any(duplicated(recoded)))
})
