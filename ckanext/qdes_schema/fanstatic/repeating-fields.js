jQuery(document).ready(function () {
    'use strict';

    // Show superseded alert.
    function related_resource_replaces_relationship(element) {
        if (jQuery(element).data('field-name') === 'relationships') {
            if (jQuery(element).val() === 'replaces') {
                jQuery(element).parents('.repeater-wrapper').find('.supersede-alert').removeClass('hidden');
            } else {
                jQuery(element).parents('.repeater-wrapper').find('.supersede-alert').addClass('hidden');
            }
        }
    }

    jQuery('.repeating-field').repeater({

        show: function () {
            // Check to see if there is any select elements with an autocomplete data module
            jQuery(this).find('[data-module="qdes_autocomplete"]').map(function (index, select) {
                // Initialize autocomplete data for select element
                ckan.module.initializeElement(select);
            });
            jQuery(this).show();
        },
        hide: function (deleteElement) {
            if (confirm('Are you sure you want to remove this item?')) {
                // Remove value and trigger events
                jQuery(this).hide();
                jQuery(this).find('.form-control, [data-module="qdes_autocomplete"]').val('').blur().change();
            }
        },
        ready: function (setIndexes) {

        },
        isFirstItemUndeletable: true
    });

    function collate_inputs(repeater_id, target_field_id, field_type) {
        var multi_groups = jQuery('#' + repeater_id + ' [data-repeater-item]:visible' + ' [data-group="True"]')
        var collated_values = [];

        if (multi_groups.length > 0) {
            multi_groups.each(function () {
                var value = jQuery(this).val().trim();
                if (value && value.length > 0) {
                    var field_name = jQuery(this).data('field-name');
                    // Find the parent element index
                    var parentElement = jQuery(this).parents('#' + repeater_id + ' [data-repeater-item]:visible').first()
                    var parentIndex = jQuery('#' + repeater_id + ' [data-repeater-item]:visible').index(parentElement);
                    // Get multi_group or initialize a new one if it does not exist
                    var multi_group = collated_values[parentIndex] || {};
                    multi_group[field_name] = value;
                    collated_values[parentIndex] = multi_group;
                }
            });
        }
        else {
            jQuery('#' + repeater_id + ' ' + field_type + '.form-control, #' + repeater_id + ' ' + field_type + '[data-module="qdes_autocomplete"]').each(function () {
                var value = jQuery(this).val();

                if (value && value.trim().length > 0) {
                    collated_values.push(jQuery(this).val());
                }
            });
        }

        if (Array.isArray(collated_values) && collated_values.length > 0) {
            jQuery('#' + target_field_id).val(JSON.stringify(collated_values));
        }
        else {
            jQuery('#' + target_field_id).val('');
        }
    }

    function update_repeater_fields(element) {
        var parent_field_name = jQuery(element).data('parent-field-name');
        var field_name = jQuery(element).data('field-name');
        var repeater_id = parent_field_name ? parent_field_name + '-repeater' : field_name + '-repeater';
        var target_field_id = parent_field_name ? 'field-' + parent_field_name : 'field-' + field_name;
        var field_type = jQuery('#' + repeater_id).data('field-type');

        collate_inputs(repeater_id, target_field_id, field_type);
        related_resource_replaces_relationship(element);
    }

    // Listen to repeatable fields.
    jQuery(document).on('blur', ".repeating-field .form-control", function () {
        update_repeater_fields(this);
    });
    jQuery(document).on('change', ".repeating-field .form-control", function () {
        related_resource_replaces_relationship(this);
    });

    jQuery(document).on('change', ".repeating-field [data-module='qdes_autocomplete']", function () {
        update_repeater_fields(this);
    });

    // On load trigger the on change/blur for repeatable fields,
    // otherwise required fields won't have value by default.
    jQuery(".repeating-field .form-control").blur();
    jQuery(".repeating-field [data-module='qdes_autocomplete']").change();
});
