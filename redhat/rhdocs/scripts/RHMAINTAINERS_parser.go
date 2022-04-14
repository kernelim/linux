package main

import (
	"bufio"
	"fmt"
	"log"
	"strings"
	"os"
)

type rh_label struct {
	name string
	readyForMergeDeps string
	newLabels string
	emailLabel string // I:
}

type rh_user struct {
	name string // M: FirstName LastName
	email string // M: <email>
	//gitlabUsername string
}

type rh_paths struct {
	includes []string // F:
	includeRegexes []string // N:
	excludes []string // X:
}

type rh_entry struct {
	name string	// Title
	labels rh_label // I:
	status string // 'Maintained'
	maintainers []rh_user // M:
	reviewers []rh_user // R:
	paths rh_paths // F:, N:, X:
	mailist string // L:
	tree string
}

var entries []rh_entry
var entry rh_entry

func whiteSpace(target string, remove string) string {
	newString := strings.Trim(target, remove)
	newString = strings.TrimSpace(newString)
	return newString
}

func parseNameAndEmail(target string) rh_user {
	// The string format is always FirstName LastName <user@email.com>
	name := rh_user{}
	s := strings.Split(target, "<")
	name.name = strings.TrimSpace(s[0])
	s = strings.Split(s[1], ">")
	name.email = strings.TrimSpace(s[0])
	return name
}

func displayEntry(entry rh_entry, comments bool) {
	// subsystem
	fmt.Printf(
" - subsystem: %s\n", entry.name)

	// labels section
	fmt.Printf(
"   labels:\n")
	if comments {
		fmt.Println(
"     # This is for the subsystem webhook. This will add Subsystem:net\n",
"     # to all relevant merge requests.",)
	}
	if comments || entry.labels.name != "" {
		fmt.Printf(
"     name: %s\n", entry.labels.name)
	}
	if comments {
		fmt.Println(
"     # Optional additional labels that are required for the\n",
"     # readyForMerge label. This is for the net subsystem's testing\n",
"     # efforts. See\n",
"     # https://gitlab.com/cki-project/kernel-webhooks/-/issues/56")
	}
	if comments || entry.labels.readyForMergeDeps != "" {
		fmt.Printf(
"     readyForMergeDeps:\n")
		if entry.labels.readyForMergeDeps != "" {
			fmt.Printf(
"       - %s\n", entry.labels.readyForMergeDeps)
		}
	}
	if comments {
		fmt.Println(
"     # Optional labels that are automatically added to all relevant merge\n",
"     # requests.")
	}
	if comments || entry.labels.newLabels != "" {
		fmt.Printf(
"     newLabels: %s\n", entry.labels.newLabels)
	}
	if comments {
		fmt.Println(
"     # Email Label used on RHKL to distinguish email")
	}
	if comments || entry.labels.emailLabel != "" {
		fmt.Printf(
"     emailLabel: %s\n", entry.labels.emailLabel)
	}

	// status
	if comments {
		fmt.Println(
"   # S:")
	}
	if comments || entry.status != "" {
		fmt.Printf(
"   status: %s\n", entry.status)
	}

	// maintainers
	if comments {
		fmt.Println(
"   # M:")
	}
	if comments || len(entry.maintainers) != 0 {
		fmt.Printf(
"   maintainers:\n")
		for _, name := range entry.maintainers {
			if strings.Contains(name.name, "\"") {
				name.name = "'" + name.name + "'"
			}
			fmt.Printf(
"     - name: %s\n", name.name)
			fmt.Printf(
"       email: %s\n", name.email)
		}
	}

	// reviewers
	if comments {
		fmt.Println(
"   # R:")
	}
	if comments || len(entry.reviewers) != 0 {
		fmt.Printf(
"   reviewers:\n")
		for _, name := range entry.reviewers {
			if strings.Contains(name.name, "\"") {
				name.name = "'" + name.name + "'"
			}
			fmt.Printf(
"     - name: %s\n", name.name)
			fmt.Printf(
"       email: %s\n", name.email)
		}
	}

	// paths
	fmt.Printf(
"   paths:\n")
	if comments {
		fmt.Println(
"       # F:")
	}
	if comments || len(entry.paths.includes) != 0 {
		fmt.Printf(
"       includes:\n")
		for _, include := range entry.paths.includes {
			fmt.Printf(
"          - %s\n", include)
		}
	}
	if comments {
		fmt.Println(
"       # N:")
	}
	if comments || len(entry.paths.includeRegexes) != 0 {
		fmt.Printf(
"       includeRegexes:\n")
		for _, includeRegex := range entry.paths.includeRegexes {
			fmt.Printf(
"          - %s\n", includeRegex)
		}
	}
	if comments {
		fmt.Println(
"       # X:")
	}
	if comments || len(entry.paths.excludes) != 0 {
		fmt.Printf(
"       excludes:\n")
		for _, exclude := range entry.paths.excludes {
			fmt.Printf(
"          - %s\n", exclude)
		}
	}

	// scm
	if comments {
		fmt.Println(
"   # T:")
	}
	if comments || entry.tree != "" {
		fmt.Printf(
"   scm: %s\n", entry.tree)
	}

	// mailingList
	if comments {
		fmt.Println(
"   # L:")
	}
	if comments || entry.mailist != "" {
		fmt.Printf(
"   mailingList: %s\n", entry.mailist)
	}
}

func main() {
	file, err := os.Open("RHMAINTAINERS")
	if err != nil {
		log.Fatal(err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)

	var start bool = true
	for scanner.Scan() {
		s := scanner.Text()
		if start {
			if strings.Contains(s, "-----------") {
				start = false
			}
			continue
		}
		// each blank line is a new section
		switch s {
		case "":
			entries = append(entries, entry)
			entry = rh_entry{}
			continue
		default:
			if strings.HasPrefix(s, "F:") {
				entry.paths.includes = append(entry.paths.includes, whiteSpace(s, "F:"))
			} else if strings.HasPrefix(s, "I:") {
				entry.labels.emailLabel = whiteSpace(s, "I:")
			} else if strings.HasPrefix(s, "L:") {
				// kernel-patches is an external list that should not be cc'd
				if strings.Contains(whiteSpace(s, "L:"), "kernel-patches@redhat.com") {
					break
				}
				entry.mailist = whiteSpace(s, "L:")
			} else if strings.HasPrefix(s, "M:") {
				entry.maintainers = append(entry.maintainers, parseNameAndEmail(whiteSpace(s, "M:")))
			} else if strings.HasPrefix(s, "N:") {
				entry.paths.includeRegexes = append(entry.paths.includeRegexes, whiteSpace(s, "N:"))
			} else if strings.HasPrefix(s, "R:") {
				entry.reviewers = append(entry.reviewers, parseNameAndEmail(whiteSpace(s, "R:")))
			} else if strings.HasPrefix(s, "S:") {
				entry.status = whiteSpace(s, "S:")
			} else if strings.HasPrefix(s, "T:") {
				entry.tree = whiteSpace(s, "T:")
			} else if strings.HasPrefix(s, "X:") {
				entry.paths.excludes = append(entry.paths.excludes, whiteSpace(s, "X:"))
			} else if strings.HasPrefix(s, "SS_LABEL:") {
				entry.labels.name = whiteSpace(s, "SS_LABEL:")
			} else if strings.HasPrefix(s, "BLOCKER_LABEL:") {
				entry.labels.readyForMergeDeps = whiteSpace(s, "BLOCKER_LABEL:")
			} else {
				entry.name = s
			}
			continue
		}
	}

	// don't forget to add the last one
	entries = append(entries, entry)

	if err := scanner.Err(); err != nil {
		log.Fatal(err)
	}

	// first element is empty.  Just delete it.
	entries := entries [1:]

	fmt.Println("---")
	fmt.Println("subsystems:")
	for count, entry := range entries {
		if count == 0 {
			displayEntry(entry, true)
		} else {
			displayEntry(entry, false)
		}
	}
}
