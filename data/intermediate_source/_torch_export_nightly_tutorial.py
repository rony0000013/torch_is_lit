# -*- coding: utf-8 -*-

"""
torch.export Nightly Tutorial
================
**Author:** William Wen, Zhengxu Chen, Angela Yi
"""

######################################################################
#
# .. warning::
#
#     ``torch.export`` and its related features are in prototype status and are subject to backwards compatibility
#     breaking changes. This tutorial provides a snapshot of ``torch.export`` usage as of PyTorch 2.1.
#
# :func:`torch.export` is the PyTorch 2.X way to export PyTorch models into
# standardized model representations, intended
# to be run on different (i.e. Python-less) environments.
#
# In this tutorial, you will learn how to use :func:`torch.export` to extract
# ``ExportedProgram``'s (i.e. single-graph representations) from PyTorch programs.
# We also detail some considerations/modifications that you may need
# to make in order to make your model compatible with ``torch.export``.
#
# **Contents**
#
# .. contents::
#     :local:

######################################################################
# Basic Usage
# -----------
#
# ``torch.export`` extracts single-graph representations from PyTorch programs
# by tracing the target function, given example inputs.
# ``torch.export.export()`` is the main entry point for ``torch.export``.
#
# In this tutorial, ``torch.export`` and ``torch.export.export()`` are practically synonymous,
# though ``torch.export`` generally refers to the PyTorch 2.X export process, and ``torch.export.export()``
# generally refers to the actual function call.
#
# The signature of ``torch.export.export()`` is:
#
# .. code:: python
#
#     export(
#         f: Callable,
#         args: Tuple[Any, ...],
#         kwargs: Optional[Dict[str, Any]] = None,
#         *,
#         dynamic_shapes: Optional[Dict[str, Dict[int, Dim]]] = None
#     ) -> ExportedProgram
#
# ``torch.export.export()`` traces the tensor computation graph from calling ``f(*args, **kwargs)``
# and wraps it in an ``ExportedProgram``, which can be serialized or executed later with
# different inputs. Note that while the output ``ExportedGraph`` is callable and can be
# called in the same way as the original input callable, it is not a ``torch.nn.Module``.
# We will detail the ``dynamic_shapes`` argument later in the tutorial.

import torch
from torch.export import export

class MyModule(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.lin = torch.nn.Linear(100, 10)

    def forward(self, x, y):
        return torch.nn.functional.relu(self.lin(x + y), inplace=True)

mod = MyModule()
exported_mod = export(mod, (torch.randn(8, 100), torch.randn(8, 100)))
print(type(exported_mod))
print(exported_mod(torch.randn(8, 100), torch.randn(8, 100)))

######################################################################
# Let's review some attributes of ``ExportedProgram`` that are of interest.
#
# The ``graph`` attribute is an `FX graph <https://pytorch.org/docs/stable/fx.html#torch.fx.Graph>`__
# traced from the function we exported, that is, the computation graph of all PyTorch operations.
# The FX graph has some important properties:
#
# - The operations are "ATen-level" operations.
# - The graph is "functionalized", meaning that no operations are mutations.
#
# The ``graph_module`` attribute is the ``GraphModule`` that wraps the ``graph`` attribute
# so that it can be ran as a ``torch.nn.Module``.

print(exported_mod)
print(exported_mod.graph_module)

######################################################################
# The printed code shows that FX graph only contains ATen-level ops (such as ``torch.ops.aten``)
# and that mutations were removed. For example, the mutating op ``torch.nn.functional.relu(..., inplace=True)``
# is represented in the printed code by ``torch.ops.aten.relu.default``, which does not mutate.
# Future uses of input to the original mutating ``relu`` op are replaced by the additional new output
# of the replacement non-mutating ``relu`` op.
#
# Other attributes of interest in ``ExportedProgram`` include:
#
# - ``graph_signature`` -- the inputs, outputs, parameters, buffers, etc. of the exported graph.
# - ``range_constraints`` and ``equality_constraints`` -- constraints, covered later

print(exported_mod.graph_signature)

######################################################################
# See the ``torch.export`` `documentation <https://pytorch.org/docs/main/export.html#torch.export.export>`__
# for more details.

######################################################################
# Graph Breaks
# ------------
#
# Although ``torch.export`` shares components with ``torch.compile``,
# the key limitation of ``torch.export``, especially when compared to ``torch.compile``, is that it does not
# support graph breaks. This is because handling graph breaks involves interpreting
# the unsupported operation with default Python evaluation, which is incompatible
# with the export use case. Therefore, in order to make your model code compatible
# with ``torch.export``, you will need to modify your code to remove graph breaks.
#
# A graph break is necessary in cases such as:
#
# - data-dependent control flow

def bad1(x):
    if x.sum() > 0:
        return torch.sin(x)
    return torch.cos(x)

import traceback as tb
try:
    export(bad1, (torch.randn(3, 3),))
except Exception:
    tb.print_exc()

######################################################################
# - accessing tensor data with ``.data``

def bad2(x):
    x.data[0, 0] = 3
    return x

try:
    export(bad2, (torch.randn(3, 3),))
except Exception:
    tb.print_exc()

######################################################################
# - calling unsupported functions (such as many built-in functions)

def bad3(x):
    x = x + 1
    return x + id(x)

try:
    export(bad3, (torch.randn(3, 3),))
except Exception:
    tb.print_exc()

######################################################################
# - unsupported Python language features (e.g. throwing exceptions, match statements)

def bad4(x):
    try:
        x = x + 1
        raise RuntimeError("bad")
    except:
        x = x + 2
    return x

try:
    export(bad4, (torch.randn(3, 3),))
except Exception:
    tb.print_exc()

######################################################################
# The sections below demonstrate some ways you can modify your code
# in order to remove graph breaks.

######################################################################
# Control Flow Ops
# ----------------
#
# ``torch.export`` actually does support data-dependent control flow.
# But these need to be expressed using control flow ops. For example,
# we can fix the control flow example above using the ``cond`` op, like so:

from functorch.experimental.control_flow import cond

def bad1_fixed(x):
    def true_fn(x):
        return torch.sin(x)
    def false_fn(x):
        return torch.cos(x)
    return cond(x.sum() > 0, true_fn, false_fn, [x])

exported_bad1_fixed = export(bad1_fixed, (torch.randn(3, 3),))
print(exported_bad1_fixed(torch.ones(3, 3)))
print(exported_bad1_fixed(-torch.ones(3, 3)))

######################################################################
# There are limitations to ``cond`` that one should be aware of:
#
# - The predicate (i.e. ``x.sum() > 0``) must result in a boolean or a single-element tensor.
# - The operands (i.e. ``[x]``) must be tensors.
# - The branch function (i.e. ``true_fn`` and ``false_fn``) signature must match with the
#   operands and they must both return a single tensor with the same metadata (for example, ``dtype``, ``shape``, etc.).
# - Branch functions cannot mutate input or global variables.
# - Branch functions cannot access closure variables, except for ``self`` if the function is
#   defined in the scope of a method.
#
# For more details about ``cond``, check out the `documentation <https://pytorch.org/docs/main/cond.html>`__.

######################################################################
# ..
#     [NOTE] map is not documented at the moment
#     We can also use ``map``, which applies a function across the first dimension
#     of the first tensor argument.
#
#     from functorch.experimental.control_flow import map
#
#     def map_example(xs):
#         def map_fn(x, const):
#             def true_fn(x):
#                 return x + const
#             def false_fn(x):
#                 return x - const
#             return control_flow.cond(x.sum() > 0, true_fn, false_fn, [x])
#         return control_flow.map(map_fn, xs, torch.tensor([2.0]))
#
#     exported_map_example= export(map_example, (torch.randn(4, 3),))
#     inp = torch.cat((torch.ones(2, 3), -torch.ones(2, 3)))
#     print(exported_map_example(inp))

######################################################################
# Constraints/Dynamic Shapes
# --------------------------
#
# Ops can have different specializations/behaviors for different tensor shapes, so by default,
# ``torch.export`` requires inputs to ``ExportedProgram`` to have the same shape as the respective
# example inputs given to the initial ``torch.export.export()`` call.
# If we try to run the ``ExportedProgram`` in the example below with a tensor
# with a different shape, we get an error:

class MyModule2(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.lin = torch.nn.Linear(100, 10)

    def forward(self, x, y):
        return torch.nn.functional.relu(self.lin(x + y), inplace=True)

mod2 = MyModule2()
exported_mod2 = export(mod2, (torch.randn(8, 100), torch.randn(8, 100)))

try:
    exported_mod2(torch.randn(10, 100), torch.randn(10, 100))
except Exception:
    tb.print_exc()

######################################################################
# We can relax this constraint using the ``dynamic_shapes`` argument of
# ``torch.export.export()``, which allows us to specify, using ``torch.export.Dim``
# (`documentation <https://pytorch.org/docs/main/export.html#torch.export.Dim>`__),
# which dimensions of the input tensors are dynamic.
#
# For each tensor argument of the input callable, we can specify a mapping from the dimension
# to a ``torch.export.Dim``.
# A ``torch.export.Dim`` is essentially a named symbolic integer with optional
# minimum and maximum bounds.
#
# Then, the format of ``torch.export.export()``'s ``dynamic_shapes`` argument is a mapping
# from the input callable's tensor argument names, to dimension --> dim mappings as described above.
# If there is no ``torch.export.Dim`` given to a tensor argument's dimension, then that dimension is
# assumed to be static.
#
# The first argument of ``torch.export.Dim`` is the name for the symbolic integer, used for debugging.
# Then we can specify an optional minimum and maximum bound (inclusive). Below, we show example usage.
#
# In the example below, our input
# ``inp1`` has an unconstrained first dimension, but the size of the second
# dimension must be in the interval [4, 18].

from torch.export import Dim

inp1 = torch.randn(10, 10, 2)

def dynamic_shapes_example1(x):
    x = x[:, 2:]
    return torch.relu(x)

inp1_dim0 = Dim("inp1_dim0")
inp1_dim1 = Dim("inp1_dim1", min=4, max=18)
dynamic_shapes1 = {
    "x": {0: inp1_dim0, 1: inp1_dim1},
}

exported_dynamic_shapes_example1 = export(dynamic_shapes_example1, (inp1,), dynamic_shapes=dynamic_shapes1)

print(exported_dynamic_shapes_example1(torch.randn(5, 5, 2)))

try:
    exported_dynamic_shapes_example1(torch.randn(8, 1, 2))
except Exception:
    tb.print_exc()

try:
    exported_dynamic_shapes_example1(torch.randn(8, 20, 2))
except Exception:
    tb.print_exc()

try:
    exported_dynamic_shapes_example1(torch.randn(8, 8, 3))
except Exception:
    tb.print_exc()

######################################################################
# Note that if our example inputs to ``torch.export`` do not satisfy the constraints
# given by ``dynamic_shapes``, then we get an error.

inp1_dim1_bad = Dim("inp1_dim1_bad", min=11, max=18)
dynamic_shapes1_bad = {
    "x": {0: inp1_dim0, 1: inp1_dim1_bad},
}

try:
    export(dynamic_shapes_example1, (inp1,), dynamic_shapes=dynamic_shapes1_bad)
except Exception:
    tb.print_exc()

######################################################################
# We can enforce that equalities between dimensions of different tensors
# by using the same ``torch.export.Dim`` object, for example, in matrix multiplication:

inp2 = torch.randn(4, 8)
inp3 = torch.randn(8, 2)

def dynamic_shapes_example2(x, y):
    return x @ y

inp2_dim0 = Dim("inp2_dim0")
inner_dim = Dim("inner_dim")
inp3_dim1 = Dim("inp3_dim1")

dynamic_shapes2 = {
    "x": {0: inp2_dim0, 1: inner_dim},
    "y": {0: inner_dim, 1: inp3_dim1},
}

exported_dynamic_shapes_example2 = export(dynamic_shapes_example2, (inp2, inp3), dynamic_shapes=dynamic_shapes2)

print(exported_dynamic_shapes_example2(torch.randn(2, 16), torch.randn(16, 4)))

try:
    exported_dynamic_shapes_example2(torch.randn(4, 8), torch.randn(4, 2))
except Exception:
    tb.print_exc()

######################################################################
# We can actually use ``torch.export`` to guide us as to which ``dynamic_shapes`` constraints
# are necessary. We can do this by relaxing all constraints (recall that if we
# do not provide constraints for a dimension, the default behavior is to constrain
# to the exact shape value of the example input) and letting ``torch.export``
# error out.

inp4 = torch.randn(8, 16)
inp5 = torch.randn(16, 32)

def dynamic_shapes_example3(x, y):
    if x.shape[0] <= 16:
        return x @ y[:, :16]
    return y

dynamic_shapes3 = {
    "x": {i: Dim(f"inp4_dim{i}") for i in range(inp4.dim())},
    "y": {i: Dim(f"inp5_dim{i}") for i in range(inp5.dim())},
}

try:
    export(dynamic_shapes_example3, (inp4, inp5), dynamic_shapes=dynamic_shapes3)
except Exception:
    tb.print_exc()

######################################################################
# We can see that the error message gives us suggested fixes to our
# dynamic shape constraints. Let us follow those suggestions (exact
# suggestions may differ slightly):

def suggested_fixes():
    inp4_dim1 = Dim('shared_dim')
    # suggested fixes below
    inp4_dim0 = Dim('inp4_dim0', max=16)
    inp5_dim1 = Dim('inp5_dim1', min=17)
    inp5_dim0 = inp4_dim1
    # end of suggested fixes
    return {
        "x": {0: inp4_dim0, 1: inp4_dim1},
        "y": {0: inp5_dim0, 1: inp5_dim1},
    }

dynamic_shapes3_fixed = suggested_fixes()
exported_dynamic_shapes_example3 = export(dynamic_shapes_example3, (inp4, inp5), dynamic_shapes=dynamic_shapes3_fixed)
print(exported_dynamic_shapes_example3(torch.randn(4, 32), torch.randn(32, 64)))

######################################################################
# Note that in the example above, because we constrained the value of ``x.shape[0]`` in
# ``dynamic_shapes_example3``, the exported program is sound even though there is a
# raw ``if`` statement.
#
# If you want to see why ``torch.export`` generated these constraints, you can
# re-run the script with the environment variable ``TORCH_LOGS=dynamic,dynamo``,
# or use ``torch._logging.set_logs``.

import logging
torch._logging.set_logs(dynamic=logging.INFO, dynamo=logging.INFO)
exported_dynamic_shapes_example3 = export(dynamic_shapes_example3, (inp4, inp5), dynamic_shapes=dynamic_shapes3_fixed)

# reset to previous values
torch._logging.set_logs(dynamic=logging.WARNING, dynamo=logging.WARNING)

######################################################################
# We can view an ``ExportedProgram``'s constraints using the ``range_constraints`` and
# ``equality_constraints`` attributes. The logging above reveals what the symbols ``s0, s1, ...``
# represent.

print(exported_dynamic_shapes_example3.range_constraints)
print(exported_dynamic_shapes_example3.equality_constraints)

######################################################################
# Custom Ops
# ----------
#
# ``torch.export`` can export PyTorch programs with custom operators.
#
#
# Currently, the steps to register a custom op for use by ``torch.export`` are:
#
# - Define the custom op using ``torch.library`` (`reference <https://pytorch.org/docs/main/library.html>`__)
#   as with any other custom op

from torch.library import Library, impl

m = Library("my_custom_library", "DEF")

m.define("custom_op(Tensor input) -> Tensor")

@impl(m, "custom_op", "CompositeExplicitAutograd")
def custom_op(x):
    print("custom_op called!")
    return torch.relu(x)

######################################################################
# - Define a ``"Meta"`` implementation of the custom op that returns an empty
#   tensor with the same shape as the expected output

@impl(m, "custom_op", "Meta")
def custom_op_meta(x):
    return torch.empty_like(x)

######################################################################
# - Call the custom op from the code you want to export using ``torch.ops``

def custom_op_example(x):
    x = torch.sin(x)
    x = torch.ops.my_custom_library.custom_op(x)
    x = torch.cos(x)
    return x

######################################################################
# - Export the code as before

exported_custom_op_example = export(custom_op_example, (torch.randn(3, 3),))
exported_custom_op_example.graph_module.print_readable()
print(exported_custom_op_example(torch.randn(3, 3)))

######################################################################
# Note in the above outputs that the custom op is included in the exported graph.
# And when we call the exported graph as a function, the original custom op is called,
# as evidenced by the ``print`` call.
#
# If you have a custom operator implemented in C++, please refer to
# `this document <https://docs.google.com/document/d/1_W62p8WJOQQUzPsJYa7s701JXt0qf2OfLub2sbkHOaU/edit#heading=h.ahugy69p2jmz>`__
# to make it compatible with ``torch.export``.

######################################################################
# Decompositions
# --------------
#
# The graph produced by ``torch.export`` by default returns a graph containing
# only functional ATen operators. This functional ATen operator set (or "opset") contains around 2000
# operators, all of which are functional, that is, they do not
# mutate or alias inputs.  You can find a list of all ATen operators
# `here <https://github.com/pytorch/pytorch/blob/main/aten/src/ATen/native/native_functions.yaml>`__
# and you can inspect if an operator is functional by checking
# ``op._schema.is_mutable``, for example:

print(torch.ops.aten.add.Tensor._schema.is_mutable)
print(torch.ops.aten.add_.Tensor._schema.is_mutable)

######################################################################
# By default, the environment in which you want to run the exported graph
# should support all ~2000 of these operators.
# However, you can use the following API on the exported program
# if your specific environment is only able to support a subset of
# the ~2000 operators.
#
# .. code:: python
#
#     def run_decompositions(
#         self: ExportedProgram,
#         decomposition_table: Optional[Dict[torch._ops.OperatorBase, Callable]]
#     ) -> ExportedProgram
#
# ``run_decompositions`` takes in a decomposition table, which is a mapping of
# operators to a function specifying how to reduce, or decompose, that operator
# into an equivalent sequence of other ATen operators.
#
# The default decomposition table for ``run_decompositions`` is the
# `Core ATen decomposition table <https://github.com/pytorch/pytorch/blob/b460c3089367f3fadd40aa2cb3808ee370aa61e1/torch/_decomp/__init__.py#L252>`__
# which will decompose the all ATen operators to the
# `Core ATen Operator Set <https://pytorch.org/docs/main/torch.compiler_ir.html#core-aten-ir>`__
# which consists of only ~180 operators.

class M(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(3, 4)

    def forward(self, x):
        return self.linear(x)

ep = export(M(), (torch.randn(2, 3),))
print(ep.graph)

core_ir_ep = ep.run_decompositions()
print(core_ir_ep.graph)

######################################################################
# Notice that after running ``run_decompositions`` the
# ``torch.ops.aten.t.default`` operator, which is not part of the Core ATen
# Opset, has been replaced with ``torch.ops.aten.permute.default`` which is part
# of the Core ATen Opset.

######################################################################
# Most ATen operators already have decompositions, which are located
# `here <https://github.com/pytorch/pytorch/blob/b460c3089367f3fadd40aa2cb3808ee370aa61e1/torch/_decomp/decompositions.py>`__.
# If you would like to use some of these existing decomposition functions,
# you can pass in a list of operators you would like to decompose to the
# `get_decompositions <https://github.com/pytorch/pytorch/blob/b460c3089367f3fadd40aa2cb3808ee370aa61e1/torch/_decomp/__init__.py#L191>`__
# function, which will return a decomposition table using existing
# decomposition implementations.

class M(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(3, 4)

    def forward(self, x):
        return self.linear(x)

ep = export(M(), (torch.randn(2, 3),))
print(ep.graph)

from torch._decomp import get_decompositions
decomp_table = get_decompositions([torch.ops.aten.t.default, torch.ops.aten.transpose.int])
core_ir_ep = ep.run_decompositions(decomp_table)
print(core_ir_ep.graph)

######################################################################
# If there is no existing decomposition function for an ATen operator that you would
# like to decompose, feel free to send a pull request into PyTorch
# implementing the decomposition!

######################################################################
# ExportDB
# --------
#
# ``torch.export`` will only ever export a single computation graph from a PyTorch program. Because of this requirement,
# there will be Python or PyTorch features that are not compatible with ``torch.export``, which will require users to
# rewrite parts of their model code. We have seen examples of this earlier in the tutorial -- for example, rewriting
# if-statements using ``cond``.
#
# `ExportDB <https://pytorch.org/docs/main/generated/exportdb/index.html>`__ is the standard reference that documents
# supported and unsupported Python/PyTorch features for ``torch.export``. It is essentially a list a program samples, each
# of which represents the usage of one particular Python/PyTorch feature and its interaction with ``torch.export``.
# Examples are also tagged by category so that they can be more easily searched.
#
# For example, let's use ExportDB to get a better understanding of how the predicate works in the ``cond`` operator.
# We can look at the example called ``cond_predicate``, which has a ``torch.cond`` tag. The example code looks like:

def cond_predicate(x):
    """
    The conditional statement (aka predicate) passed to ``cond()`` must be one of the following:
      - torch.Tensor with a single element
      - boolean expression
    NOTE: If the `pred` is test on a dim with batch size < 2, it will be specialized.
    """
    pred = x.dim() > 2 and x.shape[2] > 10
    return cond(pred, lambda x: x.cos(), lambda y: y.sin(), [x])

######################################################################
# More generally, ExportDB can be used as a reference when one of the following occurs:
#
# 1. Before attempting ``torch.export``, you know ahead of time that your model uses some tricky Python/PyTorch features
#    and you want to know if ``torch.export`` covers that feature.
# 2. When attempting ``torch.export``, there is a failure and it's unclear how to work around it.
#
# ExportDB is not exhaustive, but is intended to cover all use cases found in typical PyTorch code. Feel free to reach
# out if there is an important Python/PyTorch feature that should be added to ExportDB or supported by ``torch.export``.

######################################################################
# Conclusion
# ----------
#
# We introduced ``torch.export``, the new PyTorch 2.X way to export single computation
# graphs from PyTorch programs. In particular, we demonstrate several code modifications
# and considerations (control flow ops, constraints, etc.) that need to be made in order to export a graph.
