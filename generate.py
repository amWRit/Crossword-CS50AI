import sys
import random

from crossword import *


class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        for var in self.crossword.variables:
            domains = self.domains[var]
            for domain in self.domains[var].copy():
                if len(domain) != var.length:
                    self.domains[var].remove(domain)

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """

        revised = False

        # (i, j), where v1's ith character overlaps v2's jth character
        overlaps = self.crossword.overlaps[x, y]

        if overlaps is None:
            return False

        i, j = overlaps
        for domain_x in self.domains[x].copy():
            # if no y in Y.domain satisfies constraint for (X,Y):
            # delete x from X.domain

            satisfies = False
            for domain_y in self.domains[y]:
                if domain_x[i] == domain_y[j]:
                    satisfies = True
                    break

            if not satisfies:
                self.domains[x].remove(domain_x)
                revised = True

        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """

        queue = QueueFrontier()

        if arcs is None:
            # queue = all arcs
            arcs = self.get_all_arcs()

        for arc in arcs:
            queue.add(arc)

        # while queue non-empty:
        while not queue.empty():

            # (X, Y) = Dequeue(queue)
            arc = queue.remove()
            x, y = arc

            # if Revise(csp, X, Y):
            if self.revise(x, y):

                # if size of X.domain == 0:
                if len(self.domains[x]) == 0:
                    return False

                # for each Z in X.neighbors - {Y}:
                for z in self.crossword.neighbors(x) - {y}:
                    # Enqueue(queue, (Z,X))
                    queue.add((z, x))

        return True

    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """

        if len(assignment) == len(self.crossword.variables):
            return True

        return False

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # An assignment is consistent if it satisfies all of the constraints of the problem:
        # that is to say, all values are distinct,
        # every value is the correct length,
        # and there are no conflicts between neighboring variables.

        # https://stackoverflow.com/a/5278151

        values = assignment.values()
        if len(values) > len(set(values)):
            return False

        for var, value in assignment.items():
            if value != "" and var.length != len(value):
                return False

        keys = assignment.keys()
        # print(assignment)
        for x in keys:
            for y in keys:
                if x != y and y in self.crossword.neighbors(x):
                    overlaps = self.crossword.overlaps[x, y]

                    if overlaps is None:
                        break

                    i, j = overlaps
                    if assignment[x][i] != assignment[y][j]:
                        return False

        return True

    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        # return self.domains[var]

        choices_eliminated = {word: 0 for word in self.domains[var]}
        neighbors = self.crossword.neighbors(var)

        for domain_v in self.domains[var]:
            # loop through neighbors that aren't already assigned
            for neighbor in (neighbors - assignment.keys()):
                overlap = self.crossword.overlaps[var, neighbor]

                if overlap is None:
                    break

                i, j = overlap
                for domain_n in self.domains[neighbor]:
                    if domain_v[i] != domain_n[j]:
                        choices_eliminated[domain_v] += 1

        # https://docs.python.org/3/howto/sorting.html
        # sort the list by number of choices eliminated, ascending order default

        sorted_list = sorted(choices_eliminated.items(), key=lambda item: item[1])
        return [x[0] for x in sorted_list]

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """

        unassigned_vars = self.crossword.variables - set(assignment.keys())
        # return random.choice(list(unassigned_vars))

        remaining_values_count = {var: len(self.domains[var]) for var in unassigned_vars}
        sorted_remaining_values_count = sorted(remaining_values_count.items(), key=lambda item: item[1])

        # check if only one element in list
        # check if there is no tie
        if len(sorted_remaining_values_count) == 1 or \
                sorted_remaining_values_count[0][1] != sorted_remaining_values_count[1][1]:
            return sorted_remaining_values_count[0][0]

        # if there is tie, return variable with highest degree (most number of neighbors)
        else:
            tie_val = sorted_remaining_values_count[0][1]

            degrees_count = dict()

            # list only the variables that are tied
            for i in range(len(sorted_remaining_values_count)):
                var = sorted_remaining_values_count[i][0]
                word_length = sorted_remaining_values_count[i][1]

                # get the degrees (num of neighbors/arcs) of each tied variable
                neighbors_count = len(self.crossword.neighbors(var))
                if word_length == tie_val:
                    degrees_count[var] = neighbors_count

            sorted_degrees_count = sorted(degrees_count.items(), key=lambda item: item[1], reverse=True)
            return sorted_degrees_count[0][0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """

        if self.assignment_complete(assignment):
            return assignment
        else:
            # var = Select-Unassigned-Var(assignment, csp)
            var = self.select_unassigned_variable(assignment)
            # for value in Domain-Values(var, assignment, csp):
            for domain in self.order_domain_values(var, assignment):
                new_assignment = assignment.copy()
                new_assignment[var] = domain
                # if value consistent with assignment:
                if self.consistent(new_assignment):
                    # add {var = value} to assignment
                    assignment[var] = domain

                    neighbor_arcs = self.get_neighbor_arcs(var)
                    # print(neighbor_arcs)

                    inferences = self.inferences(neighbor_arcs, assignment)
                    if inferences is not None:
                        # add inferences to assignment
                        assignment.update(inferences)

                    # result = Backtrack(assignment, csp)
                    result = self.backtrack(assignment)

                    if result is not None:
                        return result

                    # remove {var = value} from assignment
                    assignment.pop(var)
                    # remove inferences from assignment
                    for item in inferences:
                        assignment.pop(item)

            return None

    def get_all_arcs(self):
        arcs = []
        for x in self.crossword.variables:
            for y in self.crossword.variables:
                if x != y:
                    arcs.append((x, y))

        return arcs

    # given a variable x, returns a set of all neighboring arcs {(Y,X)} where Y is a neighbor of X

    def get_neighbor_arcs(self, x):
        arcs = []
        neighbors = self.crossword.neighbors(x)
        for y in neighbors:
            arcs.append((y, x))

        return arcs

    # runs ac3 on the given list of arcs
    # if any inferences can be made (if a var has only one domain left, that can be assigned)

    def inferences(self, arcs, assignment):
        result = self.ac3(arcs)
        inferences = dict()

        if not result:
            return None
        else:
            for var in self.crossword.variables - set(assignment.keys()):
                if len(self.domains[var]) == 1:
                    inferences[var] = list(self.domains[var])[0]

        if len(inferences) == 0:
            return None
        # print(inferences)
        return inferences


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


class QueueFrontier():
    def __init__(self):
        self.frontier = []

    def add(self, arc):
        self.frontier.append(arc)

    # def contains_state(self, state):
    #     return any(node.state == state for node in self.frontier)

    def empty(self):
        return len(self.frontier) == 0

    def remove(self):
        if self.empty():
            raise Exception("empty frontier")
        else:
            arc = self.frontier[0]
            self.frontier = self.frontier[1:]
            return arc


if __name__ == "__main__":
    main()
