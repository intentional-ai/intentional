
# Installation

## Default install

The easiest way to get started with Intentional is to install the `intentional` package:

```
pip install intentional
```

This will install the core of Intentional, a small CLI utility, the conversation graph drawing functionality and a couple of basic plugins (`intentional-openai` and `intentional-terminal` to get you started).

## Bare-bone install

If you want only Intentional, with no plugin and utils, you should install `intentional-core` instead:

```
pip install intentional-core
```

## Install from source

If you plan to contribute to Intentional, you should install it from source. Clone [the repo](https://github.com/intentional-ai/intentional/) and the install the packages one by one.

Note that if you are contributing to the `intentional` package (not `intentional-core` only) the packages need to be installed in the correct order if you want to install all of them from source:

```
pip install intentional-core/
pip install plugins/intentional-openai/
pip install plugins/intentional-terminal/
pip install intentional/
```

If you forget to do so, everything will work well, but the packages will be installed from PyPI instead of being installed from your local copy.

In the same vein, most plugins only need `intentional-core` installed before them, such as:

```
pip install intentional-core/
pip install plugins/intentional-myplugin/
```

In general, most plugins don't depend on each other. However, some do: if that's the case, make sure to install those plugins first.

For example, `intentional-textual-ui` depends on `intentional-terminal`. To have a full from-source install of the entire stack, the order of installation is:

```
pip install intentional-core/
pip install plugins/intentional-terminal/
pip install plugins/intentional-textual-ui/
```
