# Copyright 2016 Delve Labs inc. <info@delvelabs.ca>

from unittest import TestCase
from easyinject import Injector


class InjectorTest(TestCase):

    def test_no_injection(self):
        injector = Injector(test="A")
        call = injector.wrap(lambda test: test + test + test)

        self.assertEqual(call(test="B"), "BBB")

    def test_injection(self):
        injector = Injector(test="A")
        call = injector.wrap(lambda test: test + test + test)

        self.assertEqual(call(), "AAA")

    def test_injection_kwargs_only(self):
        injector = Injector(test="A")
        call = injector.wrap(lambda *, test: test + test + test)

        self.assertEqual(call(), "AAA")

    def test_injection_direct_call(self):
        injector = Injector(a='A', b='A')
        value = injector.call(lambda a, b, c: a + b + c, b='B', c='C')
        self.assertEqual(value, "ABC")

    def test_inject_function_leaves_wrapped_function(self):
        injector = Injector(a='A', c='C', f=lambda c: lambda a, b: a + b + c)
        self.assertEqual(injector.f(b='B'), 'ABC')
        self.assertEqual(injector.f(a='B', b='B'), 'BBC')

    def test_nested_container(self):
        injector = Injector(a='A', b='A')
        sub = Injector(injector, b='B')
        subsub = sub.sub(c='C')

        self.assertEqual(subsub.call(lambda a, b, c: a + b + c), 'ABC')
        self.assertEqual(subsub.create(lambda a, b, c: a + b + c), 'ABC')

    def test_direct_access(self):
        injector = Injector(test="A")

        self.assertEqual("A", injector.test)

    def test_direct_access_no_data(self):
        injector = Injector()

        with self.assertRaises(AttributeError):
            injector.test

    def test_jit_instance(self):
        item = Exception()

        injector = Injector(test=lambda: item)

        self.assertIs(item, injector.test)

    def test_jit_instance_always_the_same_result(self):
        injector = Injector(test=self.__class__)

        self.assertIs(injector.test, injector.test)

    def test_dependency_chain(self):
        injector = Injector(a="A", b="B", test=lambda a, b: a + b)

        self.assertEqual(injector.test, "AB")

    def test_dependency_chain_longer(self):
        injector = Injector(a="A", b=lambda a: a, test=lambda a, b: a + b)

        self.assertEqual(injector.test, "AA")

    def test_create_instances(self):
        injector = Injector(test=Injector)

        self.assertIsInstance(injector.test, Injector)

    def test_dependency_chain_circular(self):
        injector = Injector(a="A", b=lambda test: test, test=lambda a, b: a + b)

        with self.assertRaises(RecursionError):
            injector.test


class InjectorCloseTest(TestCase):
    def setUp(test):
        test.call_list = []

        class Closer:
            def __init__(self, value='Default'):
                self.value = value

            def close(self):
                test.call_list.append(self.value)

        test.closer = Closer

    def test_close_does_nothing_by_default(self):
        injector = Injector()
        injector.close()

    def test_close_propagates_to_initial_child(self):
        injector = Injector(a=self.closer('A'), b=lambda: self.closer('B'))
        injector.close()

        self.assertEqual(['A'], self.call_list)

    def test_close_propagates_to_created_child_as_well(self):
        injector = Injector(a=self.closer('A'), b=lambda: self.closer('B'))
        injector.b
        injector.close()

        self.assertEqual(['A', 'B'], self.call_list)

    def test_close_made_in_sequence(self):
        injector = Injector(a=lambda b: self.closer('A'), b=lambda: self.closer('B'))
        injector.a
        injector.close()

        self.assertEqual(['B', 'A'], self.call_list)

    def test_close_shared_among_subinjectors(self):
        injector = Injector(a=lambda: self.closer('A'))
        sub = injector.sub(b=lambda: self.closer('B'))
        sub.b
        injector.a
        injector.close()

        self.assertEqual(['B', 'A'], self.call_list)

    def test_close_limited_to_scope(self):
        injector = Injector(a=lambda: self.closer('A'))
        sub = injector.sub(b=lambda: self.closer('B'))
        sub.b
        injector.a
        sub.close()

        self.assertEqual(['B'], self.call_list)

    def test_close_only_called_once(self):
        injector = Injector(a=lambda: self.closer('A'))
        sub = injector.sub(b=lambda: self.closer('B'))
        sub.b
        injector.a
        sub.close()
        injector.close()
        self.assertEqual(['B', 'A'], self.call_list)

    def test_delete_calls_close(self):
        injector = Injector(a=lambda: self.closer('A'))
        injector.a

        del injector

        self.assertEqual(['A'], self.call_list)

    def test_do_not_call_on_class_level(self):
        injector = Injector(a=self.closer)
        injector.close()

        self.assertEqual([], self.call_list)

    def test_call_on_instance(self):
        injector = Injector(a=self.closer)
        injector.a
        injector.close()

        self.assertEqual(['Default'], self.call_list)

    def test_clear_subinjectors_on_close(self):
        injector = Injector(a=lambda: self.closer('A'))
        sub = injector.sub(b=lambda: self.closer('B'))
        sub.b
        injector.a
        self.assertEqual(1, injector.child_count)

        del sub

        self.assertEqual(0, injector.child_count)
