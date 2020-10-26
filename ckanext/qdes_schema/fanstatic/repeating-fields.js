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
                if (jQuery(this).data('module') == "qdes_autocomplete" && jQuery(this).data('module-source') == "/api/2/util/dataset/autocomplete?incomplete=?") {
                    // Check to see if select2 has been initialised
                    if (jQuery(this).data('select2')) {
                        // Get the selected option data object eg. {"id":dataset_id, "text":dataset_title}
                        value = jQuery(this).select2('data');
                    } else if (value) {
                        // This will be the value set from a post back error eg. {"id":dataset_id, "text":dataset_title}
                        value = JSON.parse(value)
                    }
                } else if (jQuery(this).data('module') == "qdes_autocomplete" && jQuery(this).data('module-source') && jQuery(this).data('module-source').indexOf('/ckan-admin/vocabulary-service/term-autocomplete/') >= 0) {
                    // Check to see if select2 has been initialised
                    if (jQuery(this).data('select2')) {
                        // Get the selected option data object eg. {"id":URI, "text":label}
                        value = jQuery(this).select2('data');
                    } else if (value) {
                        // This will be the value set from a post back error eg. {"id":URI, "text":label}
                        value = JSON.parse(value);
                    }
                    if (value) {
                        // We only want to store the id which is the vocabulary URI
                        value = value.id;
                    }
                }
                if (value) {
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
                var value = jQuery(this).val().trim();
                if (jQuery(this).data('module') == "qdes_autocomplete" && jQuery(this).data('module-source') == "/api/2/util/dataset/autocomplete?incomplete=?") {
                    // Check to see if select2 has been initialised
                    if (jQuery(this).data('select2')) {
                        // Get the selected option data object eg. {"id":dataset_id, "text":dataset_title}
                        value = jQuery(this).select2('data');
                    } else if (value) {
                        // This will be the value set from a post back error eg. {"id":dataset_id, "text":dataset_title}
                        value = JSON.parse(value)
                    }
                    if (value) {
                        collated_values.push(value);
                    }
                } else if (jQuery(this).data('module') == "qdes_autocomplete" && jQuery(this).data('module-source') && jQuery(this).data('module-source').indexOf('/ckan-admin/vocabulary-service/term-autocomplete/') >= 0) {
                    // Check to see if select2 has been initialised
                    if (jQuery(this).data('select2')) {
                        // Get the selected option data object eg. {"id":URI, "text":label}
                        value = jQuery(this).select2('data');
                    } else if (value) {
                        // This will be the value set from a post back error eg. {"id":URI, "text":label}
                        value = JSON.parse(value);
                    }
                    if (value) {
                        // We only want to store the id which is the vocabulary URI
                        collated_values.push(value.id);
                    }
                }
                else {
                    if (value && value.length > 0) {
                        collated_values.push(value);
                    }
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

    // jQuery('.repeating-field .form-control').not('[data-parent-field-name="related_resources"]').blur();
    // jQuery(".repeating-field [data-module='qdes_autocomplete']").not('[data-parent-field-name="related_resources"]').change();

    // Separate logic for existing related resources
    jQuery("#existing-related-resources a.remove").on('click', function (e) {
        e.preventDefault();
        // get the data-resource and data-relationship values from the remove button
        console.log(this);

        // iterate through the `related_resources` field and remove the item
        var related_resources = JSON.parse(jQuery('textarea[name="existing_related_resources"]').val())
        var resource = jQuery(this).data('resource');
        var relationship = jQuery(this).data('relationship');

        for (let index = 0; index < related_resources.length; index++) {
            const item = related_resources[index];
            console.log(item);
            if (item['resource']['id'] == resource && item['relationship'] == relationship) {
                related_resources.splice(index, 1);
                console.log(related_resources);
            }
        }

        if (Array.isArray(related_resources) && related_resources.length > 0) {
            jQuery('textarea[name="existing_related_resources"]').val(JSON.stringify(related_resources));
        }
        else {
            jQuery('textarea[name="existing_related_resources"]').val('');
        }


        // remove the table rows from existing related resources table
        jQuery(this).closest('tr').remove();
        return false;
    });
});
