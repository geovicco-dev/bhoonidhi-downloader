# Cart

Backs `bhd cart` — stage scenes from a saved query into the Bhoonidhi Browse & Order cart. Scenes are routed automatically to the portal's direct-download, on-order, or priced cart based on their access type.

## Command handlers

::: bhoonidhi_downloader.core.cart.command.run_cart_add

::: bhoonidhi_downloader.core.cart.command.run_cart_list

::: bhoonidhi_downloader.core.cart.command.run_cart_rm

## Routing and request shaping

::: bhoonidhi_downloader.core.cart.utils.cart_kind_for

::: bhoonidhi_downloader.core.cart.utils.cart_availability_of

::: bhoonidhi_downloader.core.cart.utils.cart_kinds_for_states

::: bhoonidhi_downloader.core.cart.utils.build_add_payload

::: bhoonidhi_downloader.core.cart.utils.build_delete_payload

::: bhoonidhi_downloader.core.cart.scene_spec.make_interface_obj
