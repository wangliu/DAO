#!/usr/bin/python2
import calendar
import random
import os
import json
import sys
from datetime import datetime
from jsutils import js_common_intro


def constrained_sum_sample_pos(n, total):
    """Return a randomly chosen list of n positive integers summing to total.
    Each such list is equally likely to occur."""

    dividers = sorted(random.sample(xrange(1, total), n - 1))
    return [a - b for a, b in zip(dividers + [total], [0] + dividers)]


def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)


def rm_file(f):
    try:
        os.remove(f)
    except OSError:
        pass


def which(program):
    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None


def determine_binary(given_binary, name):
    """
    Determines if a path to a binary is correct and if not tries to
    get a generic one by looking at the system PATH
    """
    if given_binary:
        if is_exe(given_binary):
            return given_binary
    else:
        # try to find binary in the PATH
        return which(name)
    return None


def ts_now():
    """ Return a unix timestamp representing the time in UTC right now"""
    return calendar.timegm(datetime.utcnow().utctimetuple())


def seconds_in_future(secs):
    return ts_now() + secs


def create_votes_array(amounts, succeed):
    votes = []
    total = sum(amounts)
    percentage = 0.0

    if not succeed:
        for val in amounts:
            ratio = val/float(total)
            if (percentage + ratio < 0.5):
                votes.append(True)
                percentage += ratio
            else:
                votes.append(False)
    else:
        for val in amounts:
            ratio = val/float(total)
            if percentage <= 0.5:
                votes.append(True)
                percentage += ratio
            else:
                votes.append(False)

    return votes


def arr_str(arr):
    return '[ ' + ', '.join([str(x).lower() for x in arr]) + ' ]'


def extract_test_dict(name, output):
    split = output.split('Test Results: ', 1)
    if len(split) != 2:
        print("ERROR: Could not parse '{}' output properly.\n"
              "Output was:\n{}".format(
                  name, output
              ))
        sys.exit(1)
    try:
        result = json.loads(split[1])
    except:
        print("ERROR: Could not parse '{}' output properly.\n"
              "Output was:\n{}".format(
                  name, output
              ))
        sys.exit(1)
    return result


def compare_values(a, b):
    if isinstance(a, float) ^ isinstance(b, float):
        print("ERROR: float compared with non-float")
        return False
    if isinstance(a, float):
        return abs(a - b) <= 0.01
    elif isinstance(a, basestring) and isinstance(b, int):
        return int(a) == b
    elif isinstance(b, basestring) and isinstance(a, int):
        return a == int(b)
    else:
        return a == b


def eval_test(name, output, expected_dict):
    """
    Evaluate output of a scenario and compare with expected results
        Parameters
        ----------
        name : string
        The name of the scenario to evaluate

        output : string
        The output of the script that was executed, from which we will
        extract the results

        expected_dict : dict
        A dictionary containing all the expected output from the test

        Returns
        ----------
        results : dict
        The dictionary that resulted from the parsing of the test output
    """
    tests_fail = False
    results = extract_test_dict(name, output)

    for k, v in expected_dict.iteritems():
        if k not in results:
            tests_fail = True
            print("ERROR: Did not find '{}' in the test results".format(k))
            continue
        if not compare_values(results[k], v):
            tests_fail = True
            print("ERROR: Expected {} for '{}' but got {}".format(
                v, k, results[k]
            ))

    if not tests_fail:
        print("Tests for scenario '{}' PASSED!".format(name))
    else:
        print("Tests for scenario '{}' FAILED! Script output was:\n{}".format(
            name, output)
        )
        sys.exit(1)
    return results


def write_js(name, contents, accounts_num):
    """Write a javascript file from a template, prepending common intro"""
    with open(name, "w") as f:
            f.write("{}\n{}".format(js_common_intro(accounts_num), contents))


def create_genesis(accounts):
    """Create a genesis block with ether allocation for the given accounts"""
    genesis = {}
    config = {}
    config["homesteadBlock"] = "0"
    genesis["config"] = config
    genesis["nonce"] = "0xdeadbeefdeadbeef"
    genesis["timestamp"] = "0x0"
    # Start after homesteam
    genesis["parentHash"] = (
        "0x0000000000000000000000000000000000000000000000000000000000000000"
    )
    genesis["extraData"] = "0x0"
    genesis["gasLimit"] = "0x47e7c4"
    genesis["difficulty"] = (
        "0x0000000000000000000000000000000000000000000000000000000000000001"
    )
    genesis["mixhash"] = (
        "0x0000000000000000000000000000000000000000000000000000000000000000"
    )
    alloc = {}
    for acc in accounts:
        alloc[acc] = {"balance": "133700000000000000000000000000000000"}
    genesis["alloc"] = alloc
    with open('genesis_block.json', "w") as f:
        f.write(json.dumps(genesis))


def count_token_votes(amounts, votes):
    """Returns how many tokens votes yay and how many voted nay"""
    yay = 0
    nay = 0
    for idx, amount in enumerate(amounts):
        if votes[idx]:
            yay += amount
        else:
            nay += amount
    return yay, nay


def edit_dao_source(contracts_dir, keep_limits, halve_minquorum):
    with open(os.path.join(contracts_dir, 'DAO.sol'), 'r') as f:
        contents = f.read()

    # remove all limits that would make testing impossible
    if not keep_limits:
        contents = contents.replace(" || _debatingPeriod < 1 weeks", "")
        contents = contents.replace(" || (_debatingPeriod < 2 weeks)", "")
        contents = contents.replace("|| now > p.votingDeadline + 41 days", "")
        contents = contents.replace("now < closingTime + 40 days", "true")
        contents = contents.replace(
            "daoCreator.createDAO(_newServiceProvider, 0, now + 42 days);",
            "daoCreator.createDAO(_newServiceProvider, 0, now + 20);"
        )

    if halve_minquorum:  # if we are testing halve_minquorum remove year limit
        contents = contents.replace(
            "if (lastTimeMinQuorumMet < (now - 52 weeks)) {",
            "if (lastTimeMinQuorumMet < now) {"
        )

    # add test query functions
    contents = contents.replace(
        "contract DAO is DAOInterface, Token, TokenSale {",
        """contract DAO is DAOInterface, Token, TokenSale {

        function splitProposalBalance(uint pid, uint sid) constant returns (uint _balance) {
            Proposal p = proposals[pid];
            if (!p.newServiceProvider) throw;
            SplitData s = p.splitData[sid];
            return s.splitBalance;
        }

        function splitProposalSupply(uint pid, uint sid) constant returns (uint _supply) {
            Proposal p = proposals[pid];
            if (!p.newServiceProvider) throw;
            SplitData s = p.splitData[sid];
            return s.totalSupply;
        }

        function splitProposalrewardToken(uint pid, uint sid) constant returns (uint _rewardToken) {
            Proposal p = proposals[pid];
            if (!p.newServiceProvider) throw;
            SplitData s = p.splitData[sid];
            return s.rewardToken;
        }

        function splitProposalNewAddress(uint pid, uint sid) constant returns (address _DAO) {
            Proposal p = proposals[pid];
            if (!p.newServiceProvider) throw;
            SplitData s = p.splitData[sid];
            return address(s.newDAO);
        }
"""
    )
    contents = contents.replace(
        'import "./TokenSale.sol";',
        'import "./TokenSaleCopy.sol";'
    )

    new_path = os.path.join(contracts_dir, "DAOcopy.sol")
    with open(new_path, "w") as f:
        f.write(contents)

    # now edit TokenSale source
    with open(os.path.join(contracts_dir, 'TokenSale.sol'), 'r') as f:
        contents = f.read()
    if not keep_limits:
        contents = contents.replace('closingTime - 2 weeks > now', 'true')
    with open(os.path.join(contracts_dir, 'TokenSaleCopy.sol'), "w") as f:
        f.write(contents)

    return new_path


def available_scenarios():
    dir = "scenarios"
    return [name for name in os.listdir(dir)
            if os.path.isdir(os.path.join(dir, name))]
