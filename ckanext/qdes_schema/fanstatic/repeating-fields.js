jQuery(document).ready(function () {
    'use strict';

    jQuery('.repeating-field').repeater({

        show: function () {
            // Check to see if there is any select elements with an autocomplete data module
            jQuery(this).find('select[data-module="autocomplete"]').map(function (index, select) {
                // Initialize autocomplete data for select element
                ckan.module.initializeElement(select);
            });
            jQuery(this).show();
        },
        hide: function (deleteElement) {
            if (confirm('Are you sure you want to remove this item?')) {
                // Remove value and trigger events
                jQuery(this).hide();
                jQuery(this).find('.form-control, select[data-module="autocomplete"]').val('').blur().change();
            }
        },
        ready: function (setIndexes) {

        },
        isFirstItemUndeletable: true
    });

    function collate_inputs(repeater_id, target_field_id, field_type) {
        var multi_groups = jQuery('#' + repeater_id + ' [data-repeater-item]:visible' + ' ' + field_type + '[data-group="True"]')
        var collated_values = multi_groups.length > 0 ? {} : [];

        if (multi_groups.length > 0) {
            multi_groups.each(function () {
                var value = jQuery(this).val();
                var field_name = jQuery(this).data('field-name');
                var field = collated_values[field_name] || []
                field.push(value)
                collated_values[field_name] = field
            });
            // Count the number of visible data-repeater-item rows
            collated_values['count'] = jQuery('#' + repeater_id + ' [data-repeater-item]:visible').length;
        }
        else {
            jQuery('#' + repeater_id + ' ' + field_type + '.form-control, #' + repeater_id + ' ' + field_type + '[data-module="autocomplete"]').each(function () {
                var value = jQuery(this).val();

                if (value && value.trim().length > 0) {
                    collated_values.push(jQuery(this).val());
                }
            });
        }

        if (Array.isArray(collated_values) && collated_values.length > 0 || Object.keys(collated_values).length > 0) {
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
    }

    jQuery(document).on('blur', ".repeating-field .form-control", function () {
        update_repeater_fields(this);
    });

    jQuery(document).on('change', ".repeating-field select[data-module='autocomplete']", function () {
        update_repeater_fields(this);
    });

});
