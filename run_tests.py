import glob
import itertools
import logging
import os
import subprocess
import sys

log = logging.getLogger(__name__)

# A test suite represents an entry in the dictionary below. The entry's key is the name of the
# suite, the entry's value is a list of keywords. A "keyword" is an argument to pytest's -k
# option. It acts as a selector for tests. Each of the keywords in the list will be run
# concurrently. If the list contains None, everything else will be run sequentially once the
# concurrently run tests are finished. Please note that keywords are matched as substrings: Foo
# will match Foo, FooBar and BarFoo.
#

test_suites = {
    'test': [
        'SortTest',
        'AWSJobStoreTest',
        'AzureJobStoreTest',
        'FileJobStoreTest',
        'GoogleJobStoreTest',
        'AwsJobStoreCacheTest',
        'AzureJobStoreCacheTest',
        'FileJobStoreCacheTest',
        'GoogleJobStoreCacheTest',
        None],
    'integration-test': [
        'CGCloudProvisionerTest'
    ]}


def run_tests(keywords, index, args):
    args = [sys.executable, '-m', 'pytest', '-vv',
            '--junitxml', 'test-report-%s.xml' % index,
            '-k', keywords] + args
    log.info('Running %r', args)
    return subprocess.Popen(args)


def main(suite, args):
    suite = test_suites[suite]
    for name in glob.glob('test-report-*.xml'):
        os.unlink(name)
    num_failures = 0
    index = itertools.count()
    pids = set()
    try:
        for keyword in suite:
            if keyword:
                process = run_tests(keyword, str(next(index)), args)
                pids.add(process.pid)
        while pids:
            pid, status = os.wait()
            pids.remove(pid)
            if os.WIFEXITED(status):
                status = os.WEXITSTATUS(status)
                if status:
                    num_failures += 1
            else:
                num_failures += 1
    except:
        for pid in pids:
            os.kill(pid, 15)
        raise

    if None in suite:
        everything_else = ' and '.join('not (%s)' % keyword
                                       for keyword in itertools.chain(*test_suites.values()))
        process = run_tests(everything_else, str(next(index)), args)
        if process.wait():
            num_failures += 1

    import xml.etree.ElementTree as ET
    testsuites = ET.Element('testsuites')
    for name in glob.glob('test-report-*.xml'):
        log.info("Reading test report %s", name)
        tree = ET.parse(name)
        testsuites.append(tree.getroot())
        os.unlink(name)
    name = 'test-report.xml'
    log.info('Writing aggregate test report %s', name)
    ET.ElementTree(testsuites).write(name, xml_declaration=True)

    if num_failures:
        log.error('%i out %i child processes failed', num_failures, next(index))

    return num_failures


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit(main(suite=sys.argv[1], args=sys.argv[2:]))
