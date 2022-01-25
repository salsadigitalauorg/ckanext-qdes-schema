(function ($) {
    $(document).ready(function () {
        var getSearchInputElSelector = function (fieldName) {
            return '.' + fieldName + '-search input';
        }
        var getHiddenInputElSelector = function () {
            return '.hidden-input textarea';
        }
        var getOtherFieldSelector = function () {
            return 'select';
        }
        var getTable = function () {
            return '.selected-tree-table';
        }
        var getTableDeleteBtnSelector = function () {
            return '.selected-tree-table a.btn';
        }
        var objectExistInArray = function (objArray, obj) {
            var i = -1;
            objArray.forEach(function (item, index) {
                if (JSON.stringify(item) === JSON.stringify(obj)) {
                    i = index;
                }
            });

            return i;
        }
        var delayMe = function (f, delay) {
            var timer = null;
            return function () {
                var context = this, args = arguments;
                clearTimeout(timer);
                timer = window.setTimeout(function () {
                    f.apply(context, args);
                }, delay || 500);
            };
        }
        var addTableRow = function ($table, cols, item, heading = false) {
            var $row = heading ? $('<tr/>') : $('<tr/>');
            cols.forEach(function (item, index) {
                if (heading) {
                    $row.append('<th>' + item + '</th>');
                } else {
                    $row.append('<td>' + item + '</td>');
                }
            });

            if (!heading) {
                $row.append('<td><a class="btn btn-danger btn-xs">Delete</a></td>');
                $row.find('a.btn').data('data-item-json', item);
                $table.find('tbody').append($row);
            } else {
                $row.append('<th>&nbsp;</th>');
                $table.find('thead').append($row);
            }
        }
        var initTableHeadings = function ($table, fieldNames) {
            addTableRow($table, fieldNames, '', true);
        }
        var adjustCss = function (selector) {
            if (selector == undefined) {
                selector = 'ul.fancytree-container, ul.fancytree-container ul';
            }
            $(selector).each(function (i, ul) {
                var allchildren = $(ul).children();
                var visible_li = null;
                allchildren.each(function (j, li) {
                    var li$ = $(li);
                    if (li$.children().hasClass('fancytree-hide')) {
                        li$.removeClass(
                            'fancytree-show fancytree-first-visible fancytree-last-visible');
                    } else {
                        li$.addClass('fancytree-show');
                        li$.removeClass('fancytree-last-visible');
                        if (visible_li == null) {
                            li$.addClass('fancytree-first-visible');
                        } else {
                            li$.removeClass('fancytree-first-visible');
                        }
                        visible_li = li;
                    }
                });
                if (visible_li != null) {
                    $(visible_li).addClass('fancytree-last-visible');
                }
            });
        }
        var initTree = function ($treeWrapper, dataModelPath) {
            $treeWrapper.find('.tree')
                .fancytree({
                    extensions: ["filter"],
                    source: {
                        url: dataModelPath,
                        cache: true,
                    },
                    filter: {
                        autoExpand: true,
                        mode: "hide",
                        nodata: 'No matches for filter.'
                    },
                    icon: false,
                    counter: true,
                    clickFolderMode: 3,
                    init: function (e, data) {
                        var $wrapperEl = data.tree.$container.closest('.tree-wrapper');
                        $wrapperEl.find(getHiddenInputElSelector()).change();
                    },
                    expand: function (e, data) {
                        // Only need to adjust the CSS of the node that was
                        // just opened.
                        adjustCss(data.node.ul);
                    },
                    dblclick: function (e, data) {
                        var $wrapperEl = data.node.tree.$container.closest('.tree-wrapper');
                        var fieldName = $wrapperEl.attr('data-fieldname');
                        var isMultiGrp = $wrapperEl.hasClass('tree-multi-group');

                        // Add the selected tree node to search field.
                        $wrapperEl.find(getSearchInputElSelector(fieldName)).val(data.node.title);
                        $wrapperEl.find(getSearchInputElSelector(fieldName)).attr('data-selected-node-tree', data.node.key);

                        // Enable add button.
                        var enableButton = false;
                        if (isMultiGrp) {
                            // If it is group field, need to check the other field already selected or not.
                            if ($wrapperEl.find('select').val().length > 0) {
                                enableButton = true;
                            }
                        } else {
                            enableButton = true;
                        }
                        if (enableButton) {
                            $wrapperEl.find('.add-selected-node-tree').removeAttr('disabled');
                        }

                        // Support for quantityKind.
                        //
                        // If selected node is parent, collect all children quantity_kind.
                        // If selected node is not parent, collect current quantity_kind.
                        // If quantity_kind array is null, show all available option.
                        // If quantity_kind array is not null, show only option that has the same quantity_kind,
                        // check the js variable for the option, and then re-render the dropdown.
                        if (isMultiGrp) {
                            var selectEl = $wrapperEl.find('select')
                            var selectOptionVar = window[selectEl.attr('data-field-name').replace(/-/g, '')]
                            var quantityKinds = []
                            var getQuantityKinds = function (item) {
                                if (item.data.quantity_kind !== null && quantityKinds.indexOf(item.data.quantity_kind) === -1) {
                                    quantityKinds.push(item.data.quantity_kind)
                                }

                                if (item.children !== null) {
                                    item.children.forEach(function (childItem) {
                                        getQuantityKinds(childItem)
                                    });
                                }
                            }
                            
                            // Get all quantity kinds recursively.
                            getQuantityKinds(data.node)

                            // Is dimensionless?
                            var isDimensionless = false
                            quantityKinds.forEach(function (item) {
                                if (item.toLowerCase().includes('dimensionless') || item.toLowerCase().includes('dimensionlessratio')) {
                                    isDimensionless = true
                                }
                            })

                            // Re-render the dropdown.
                            selectEl.html('')
                            if (quantityKinds.length > 0 && !isDimensionless) {
                                // Collect all quantity kind options.
                                selectEl.append('<option title="" value=""></option>')
                                selectOptionVar.forEach(function (item) {
                                    if (quantityKinds.indexOf(item.quantity_kind) > -1) {
                                        selectEl.append('<option title="' + item.title + '" value="' + item.value + '">' + item.text + '</option>')
                                    }
                                })
                            }
                            else {
                                // Render all if no quantity kinds or there is dimensionless.
                                selectOptionVar.forEach(function (item) {
                                    selectEl.append('<option title="' + item.title + '" value="' + item.value + '">' + item.text + '</option>')
                                })
                            }
                        }
                    },
                    enhanceTitle: function (e, data) {
                        if (data.node.children !== null) {
                            data.$title.html(data.node.title + '&nbsp; <i>(' + data.node.children.length + ')</i>')
                        }

                    }
                })
                .on('mouseenter mouseleave', 'span.fancytree-title', function (event) {
                    var node = $.ui.fancytree.getNode(event);
                    if (event.type === 'mouseenter') {
                        $('.tooltip').remove();
                        // Render tooltip.
                        $(this)
                            .attr('data-container', 'body')
                            .attr('data-placement', 'right')
                            .attr('data-original-title', node.data.definition)
                            .tooltip('show');
                    } else {
                        // Disable tooltip.
                        $(this).tooltip('hide');
                    }

                });
        }

        var $treeWrapperEl = $('.tree-wrapper');
        $treeWrapperEl.each(function () {
            // Get the model url.
            var dataModelPath = $(this).attr('data-model');
            var fieldName = $(this).attr('data-fieldname');
            var fieldLabel = $(this).attr('data-fieldlabel');
            var isMultiGrp = $(this).hasClass('tree-multi-group');
            var $otherFieldEl = $(this).find(getOtherFieldSelector());

            if (dataModelPath.length > 0) {
                initTree($(this), dataModelPath);
            }

            // Init table headings.
            if (isMultiGrp) {
                var otherFieldLabel = $otherFieldEl.closest('.form-group').find('label').text();
                initTableHeadings($(this).find(getTable()), [fieldLabel, otherFieldLabel]);
            } else {
                initTableHeadings($(this).find(getTable()), [fieldLabel]);
            }


            // Setup event listener on search.
            $(this).find('.' + fieldName + '-search input').on('keyup', delayMe(function (e) {
                if (e.which !== 32) {
                    var $wrapperEl = $(this).closest('.tree-wrapper');
                    var tree = $.ui.fancytree.getTree($wrapperEl.find('.tree'));
                    var val = $(this).val().trim();
                    val = val.replace(/\s+/g, '');

                    if (val.length > 1) {
                        tree.filterNodes($(this).val(), {
                            autoExpand: true
                        });
                    } else {
                        tree.clearFilter();
                        tree.expandAll(false);
                    }
                }
            }));

            // Setup event listener to add button.
            $(this).find('.add-selected-node-tree').on('click', function () {
                var $wrapperEl = $(this).closest('.tree-wrapper');
                var fieldName = $wrapperEl.attr('data-fieldname');
                var $hiddenEl = $wrapperEl.find(getHiddenInputElSelector());
                var $searchInputEl = $wrapperEl.find(getSearchInputElSelector(fieldName));
                var $otherFieldEl = $wrapperEl.find(getOtherFieldSelector());
                var selectedNode = $searchInputEl.attr('data-selected-node-tree');
                var isMultiGrp = $wrapperEl.hasClass('tree-multi-group');
                var val = $hiddenEl.val();
                var tree = $.ui.fancytree.getTree($wrapperEl.find('.tree'));
                var valObj = [];
                var selectedValue = {};

                // Get existing value if any.
                if (val.length > 0) {
                    valObj = JSON.parse(val);
                }

                // Build value.
                if (isMultiGrp) {
                    selectedValue[fieldName] = selectedNode;
                    selectedValue[$otherFieldEl.attr('data-field-name')] = $otherFieldEl.val();
                } else {
                    selectedValue = selectedNode;
                }

                // Only add if the value is not exist.
                if (objectExistInArray(valObj, selectedValue) === -1) {
                    valObj.push(selectedValue);
                }

                // Add value to hidden field.
                $hiddenEl.val(JSON.stringify(valObj));

                // Trigger change event so that other listener can react to it.
                $hiddenEl.change();

                // Remove data-selected-node-tree.
                $searchInputEl.removeAttr('data-selected-node-tree');

                // Remove value on the search input.
                $searchInputEl.val('');
                $searchInputEl.keyup();

                // Remove value on the other field
                if (isMultiGrp) {
                    // Reset.
                    var selectOptionVar = window[$otherFieldEl.attr('data-field-name').replace(/-/g, '')]
                    $otherFieldEl.html('');
                    selectOptionVar.forEach(function (item) {
                        $otherFieldEl.append('<option title="' + item.title + '" value="' + item.value + '">' + item.text + '</option>')
                    });

                    $otherFieldEl.val('');
                    $otherFieldEl.change();
                }

                // Disable add button.
                $(this).attr('disabled', 'disabled');

                // Clear filter and reset tree.
                tree.clearFilter();
                tree.expandAll(false);
            });

            // Listen to hidden field change event and update the table.
            $(this).find(getHiddenInputElSelector()).on('change', function () {
                var $wrapperEl = $(this).closest('.tree-wrapper');
                var $tableEl = $wrapperEl.find(getTable());
                var $otherFieldEl = $wrapperEl.find(getOtherFieldSelector());
                var fieldName = $wrapperEl.attr('data-fieldname');
                var tree = $.ui.fancytree.getTree($wrapperEl.find('.tree'));
                var isMultiGrp = $wrapperEl.hasClass('tree-multi-group');
                var val = $(this).val();
                var valObj = [];

                // If has value, then show the table.
                if (val.length > 0 && JSON.parse(val).length > 0) {
                    $wrapperEl.find('.no-selected-node-tree').hide();
                    $wrapperEl.find('.has-selected-node-tree').show();

                    // Get the json obj.
                    valObj = JSON.parse(val);

                    // Reset the table body.
                    $tableEl.find('tbody').empty();

                    // Iterate each obj and render the row.
                    valObj.forEach(function (item, index) {
                        if (isMultiGrp) {
                            var otherFieldVal = item[$otherFieldEl.attr('data-field-name')]
                            var otherFieldLabel = $otherFieldEl.find('option[value="' + otherFieldVal + '"]').text()
                            var cols = [
                                tree.getNodeByKey(item[fieldName]).title,
                                otherFieldLabel
                            ];
                            addTableRow($tableEl, cols, JSON.stringify(item));
                        } else {
                            addTableRow($tableEl, [tree.getNodeByKey(item).title], JSON.stringify(item));
                        }
                    });
                } else {
                    $wrapperEl.find('.has-selected-node-tree').hide();
                    $wrapperEl.find('.no-selected-node-tree').show();
                }
            });

            // For multi group field, listen the other field,
            // currently hardcoded to always listen the select field on second field.
            if (isMultiGrp) {
                $(this).find('select').on('change', function () {
                    var $wrapperEl = $(this).closest('.tree-wrapper');
                    var $searchInputEl = $wrapperEl.find(getSearchInputElSelector(fieldName));
                    var selectedNode = $searchInputEl.attr('data-selected-node-tree');

                    // If both field are filled, then enable the button.
                    if (selectedNode !== undefined && selectedNode.length > 0 && $(this).val().length > 0) {
                        $wrapperEl.find('.add-selected-node-tree').removeAttr('disabled');
                    } else {
                        $wrapperEl.find('.add-selected-node-tree').attr('disabled', 'disabled');
                    }
                });
            }
        });

        // Listen to delete button.
        $(document).on('click', getTableDeleteBtnSelector(), function (e) {
            e.preventDefault();

            var $wrapperEl = $(this).closest('.tree-wrapper');
            var fieldName = $wrapperEl.attr('data-fieldname');
            var $hiddenEl = $wrapperEl.find(getHiddenInputElSelector());
            var obj = JSON.parse($(this).data('data-item-json'));
            var val = JSON.parse($hiddenEl.val());
            var index = objectExistInArray(val, obj);

            val.splice(index, 1);
            if (val.length > 0) {
                $hiddenEl.val(JSON.stringify(val));
            } else {
                $hiddenEl.val('');
            }
            $hiddenEl.change();
        });
    });
})($);
