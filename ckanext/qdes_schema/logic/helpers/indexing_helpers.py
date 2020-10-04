from ckan.plugins.toolkit import h


def get_resource_format_labels(package_type, resource_formats):
    resource_format_labels = []

    # Only perform this step if the package type is "dataset" (and we have some resources)
    if package_type in ['dataset'] and resource_formats:
        schema = h.scheming_get_dataset_schema('dataset')
        schema_field = h.scheming_field_by_name(schema['resource_fields'], 'format') if schema else []
        schema_field_choices = h.scheming_field_choices(schema_field) or []

        for format in resource_formats:
            # The `scheming_choices_label` helper returns the
            # original value if no matching choice found
            resource_format_labels.append(h.scheming_choices_label(schema_field_choices, format))

    return resource_format_labels
