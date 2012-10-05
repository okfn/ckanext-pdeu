import os
import nose

# These are tests that we want to skip because they would fail due to
# deliberate changes that publicdata.eu customisations make to CKAN.
TEST_METHODS_TO_SKIP = [
  'ckan.tests.functional.api.test_util.TestUtil.test_status',
]


class PDEUNosePlugin(nose.plugins.Plugin):
    name = 'PDEUNosePlugin'

    def options(self, parser, env=os.environ):
        super(PDEUNosePlugin, self).options(parser, env=env)

    def configure(self, options, conf):
        super(PDEUNosePlugin, self).configure(options, conf)
        self.enabled = True
        self.skipped_tests = []

    def wantMethod(self, method):
        # Skip any methods from skip_methods.
        for test_method_to_skip in TEST_METHODS_TO_SKIP:
            test_class, test_method = test_method_to_skip.rsplit('.', 1)
            if test_class in str(getattr(method, 'im_class', None)):
                if test_method == method.__name__:
                    self.skipped_tests.append(
                        test_class + '.' + method.__name__)
                    return False
        return None

    def finalize(self, result):
        import pprint
        print "PDEUNosePlugin skipped {} tests:".format(
                len(self.skipped_tests))
        pprint.pprint(self.skipped_tests)
