odoo.define('web_cosultant.code_search', function (require) {
'use strict';

 var website = require('website.website'),
        base = require('web_editor.base'),
        core = require('web.core'),
        ajax = require('web.ajax'),
        wp = $('#website_partner').data('website-partner'),
        op = $('#order_partner').data('order-partner'),
        state = (op == wp) ? true : false,
        $consultant_add_item = $("#consultant_add_item"),
        _t = core._t;
        require('web.dom_ready');



        $("#consultant_add_item").on('click', function(){

           $.ajax({
                url: '/code_sale?search=' +$("#search_consultant_code").val() ,
                data: {search_code: $("#search_consultant_code").val(),
                },

            }).done(function (data) {
                var code= $("#search_consultant_code").val()
                window.location.href = '/code_sale?search='+ $("#search_consultant_code").val() + "&qty=" + $("#add_qty_cons").val();
            });

            });
            //             $("[id*='qty_consult_order']").on("change paste keyup", function() {

        $("[id*='qty_consult_order']").on("change paste keyup", function() {
               $.ajax({
                url: '/code_sale' ,
                data: {quantity_product_id: $(this).val(),
                       product_id_cons: $(this).attr("data-product-id")
                },

            });

            });

        $("#down_qty_search_cons").on('click', function(){
            var code= parseInt($("#add_qty_cons").val())-1;
            if (code <= 0){
                code=1
                alert('La cantidad debe ser mayor que 0');
                }
            $("#add_qty_cons").val(code);
            });

        $("#up_qty_search_cons").on('click', function(){
            var code= parseInt($("#add_qty_cons").val())+1;
            $("#add_qty_cons").val(code);
            });

        $("[id*='remove_consultant']").on('click', function(){

           $.ajax({
                url: '/code_sale' ,
                data: { line_id_cons: $(this).attr("data-line-id"),
                },

            }).done(function (data) {
                window.location.href = '/code_sale';
            });

            });

});

