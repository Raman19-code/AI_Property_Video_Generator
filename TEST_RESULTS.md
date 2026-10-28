# Test Results

**Result: 94 passed, 0 failed** in 131 seconds. The full log is in `tests/last_test_run.txt`.

| | |
|---|---|
| Date | 28 Oct 2026 |
| Machine | Linux sandbox (not Windows) |
| Python | 3.13.18 |
| Libraries | streamlit 1.66.1, moviepy 2.2.1, pillow 11.3.0, numpy 2.5.3, pytest 9.1.1 |
| Command | `python -m pytest tests -v` |

| Test file | Tests | What it covers |
|---|---|---|
| `tests/test_validators.py` | 40 | Form fields and image files |
| `tests/test_script_generator.py` | 39 | Scene structure, facts-only guarantee, video length, feature-to-photo matching with labels |
| `tests/test_video_generator.py` | 11 | Text layout, export failures, two real MP4 renders |
| `tests/test_app_ui.py` | 4 | The Streamlit app, run headless, including one full generate-and-download flow |

## Coverage of the cases listed in the assignment brief

| Case | Test(s) | Result |
|---|---|---|
| Valid property details and images | `test_valid_details_accepted`, `test_valid_image_counts_accepted[4,5,8]`, `test_landscape_8_images_end_to_end` | Pass |
| Missing required details | `test_missing_required_field[...]` (5 fields), `test_all_empty_gives_many_errors_not_a_crash`, `test_empty_form_shows_friendly_errors_not_a_crash` | Pass |
| Fewer than 4 or more than 8 images | `test_wrong_image_count_rejected[0, 3, 9]`, `test_too_few_images_message_when_no_uploads`, `test_image_count_out_of_range_raises` | Pass |
| Unsupported image formats | `test_unsupported_extension_rejected[gif, bmp, txt, pdf, no extension]`, `test_gif_renamed_to_jpg_rejected` | Pass |
| Corrupted images | `test_corrupted_image_rejected`, `test_truncated_image_rejected`, `test_empty_file_and_tiny_image_rejected`, `test_oversized_file_rejected` | Pass |
| Long property names and captions | `test_long_name_and_features_rejected`, `test_maximum_allowed_name_is_accepted`, `test_long_name_overlay_stays_inside_margins` (landscape and vertical), `test_long_feature_lines_are_shrunk_or_wrapped_not_overflowing`, `test_single_giant_word_is_split`, `test_long_name_and_captions_stay_intact_in_script` | Pass |
| Missing contact details | `test_missing_contact_is_warning_not_error`, `test_missing_contact_is_omitted_from_closing_scene`, `test_vertical_format_with_mixed_aspect_ratios` (renders a video without contact) | Pass |
| Video export failures | `test_encoder_failure_becomes_friendly_error_and_leaves_no_files` (simulated "disk full"), `test_unwritable_output_folder_is_friendly_error`, `test_image_scene_mismatch_is_friendly_error`, `test_invalid_video_size_rejected` | Pass |
| Missing audio or optional AI API credentials | `test_no_api_keys_needed`. The app has no audio and no API dependency, and `test_landscape_8_images_end_to_end` asserts the MP4 has no audio track | Pass |
| Successful MP4 generation | `test_landscape_8_images_end_to_end`, `test_vertical_format_with_mixed_aspect_ratios`, `test_sample_property_end_to_end_in_the_ui` | Pass |
| Video has the required scenes, captions and final enquiry prompt | `test_one_scene_per_image_with_required_structure[4..8]` (hook, intro, closing with call-to-action and contact), and the 8-image render test, which reads the last frame of the MP4 and checks for large white call-to-action text and the gold contact line | Pass |
| Facts only, nothing invented | `test_grounding_check_catches_invented_claims`, `test_templates_contain_no_marketing_superlatives`, `test_features_are_used_verbatim_and_only_from_user`, `test_too_many_features_are_reported_not_invented`, `test_price_in_script_matches_input_exactly` | Pass |
| Features shown with the matching photo | `test_each_feature_is_shown_with_its_matching_photo`, `test_match_score_handles_plurals_case_and_unrelated_words`, `test_unmatched_feature_is_never_placed_on_a_wrongly_labelled_photo`, `test_unmatched_features_use_photos_without_a_label`, `test_labelled_photo_without_matching_feature_becomes_a_label_card`, `test_at_most_three_features_per_photo`, `test_without_labels_behaviour_is_unchanged`, `test_label_validation`, and the UI test (scene 3 caption is `Bedroom | 3 bedrooms | Wardrobes in every bedroom`) | Pass |
| Length 20-40 seconds | `test_video_length_is_between_20_and_40_seconds[4..8]`, and the render test compares the real MP4 duration with the plan | Pass |

## What each render test checks inside the MP4
* Codec is H.264, pixel format is yuv420p, size is exactly 1280x720 (or 720x1280 for vertical)
* No audio stream
* Real duration is between 20 and 40 s and matches the planned duration within 1 s
* Progress values go up to 1.0 and never go backwards
* No `.part` temporary file is left behind
* First and last frames are different, the last frame contains the call-to-action text

## Manual checks done
* Opened the app in a real Chromium browser: empty-form errors, loading the sample, generating, the `<video>` player appearing, the download buttons appearing (screenshots taken).
* Looked at extracted frames of the sample video (hook, intro, feature, closing) and at long-text overlays in landscape and vertical format.

## Not verified (be honest in the demo if asked)
* **Windows 11 and `run.bat`**: everything above ran on Linux. The code uses no Linux-only features and `run.bat` is a plain script, but it has not been run on Windows. Run it once before the demo.
* **Playback in Chrome/Edge on Windows**: the MP4 uses H.264 + yuv420p, which those browsers support, and the file decodes correctly with FFmpeg. The headless test browser used here cannot play H.264, so real playback was not observed.
* **Python 3.10-3.12**: only 3.13 was run.
* **Render speed on an 8 GB laptop**: a 30 s video took about 45-50 s here.
