#!/usr/local/bin/perl -wT
# Translate webpages to the dialect spoken in Berlin, Germany
# NAVBAR muss noch eingebaut werden auch in slowdeath
use strict;
{
    ##### Package Berlinifyer start #####
    package Berlinifyer;
    use base "HTML::Parser";
   
    my $berlinified = undef; # String, where CGI-output is saved
    my $new_query = "http://user.cs.tu-berlin.de/~ramiro/cgi-bin/berlinifyer.cgi?url=";

    my ($regex_url,$base_url) = undef;
    sub set_urls {
	my $self = shift;
	($regex_url, $base_url) = @_;
    }

    # return berlinified
    sub get_berlinified { return $berlinified; }

    # substitute words and letters
    sub substitute {
	my $vowel = 'aeiouäöü';
	my $line = shift;
	my %subst_words = ('An der' => 'Anna',
			   'an der' => 'anna',
			   'An die' => 'Anne',
			   'an die' => 'anne',
			   'Auch' => 'Och',
			   'auch' => 'och',
			   'Auf' => 'Uff',
			   'auf' => 'uff',
			   'Du' => 'De',
			   'du' => 'de',
			   'Ich' => 'Ick',
			   'ich' => 'ick',
			   'In der' => 'Inna',
			   'in der' => 'inna',
			   'In die' => 'Inne',
			   'in die' => 'inne',
			   'Was' => 'Wat',
			   'was' => 'wat');
	
	for(keys %subst_words) {$line =~ s/(\b)$_(\b)/$1$subst_words{$_}$2/g;}
	$line =~ s^ei(\w)^ee$1^g;
	$line =~ s|(\w{2,})er([^$vowel])|$1a$2|g;
	$line =~ s|([$vowel])r([^$vowel])|$1a$2|g;
	$line =~ s|([^n])g([r$vowel])|$1j$2|g;
	$line =~ s/([^$vowel][^n])g(\b)/$1ch$2/g;
	return $line;
    }

    # Event handlers
    sub comment {
	my ($self, $comment) = @_;
	$berlinified .= "<!-- $comment -->";
    }

    sub start {
	my ($self, $tag, $attr, $attrseq, $origtext) = @_;
	# Expand relative to full url. Prepend $new_query to
	# webpage links, i.e. <a href="...">, so that linked pages
	# will be berlinified as well.
	# Applet and Object tags are currently ignored. 
	# Does not yet work properly with all imaginable URLs
	unless ($tag eq 'a' || $tag eq 'img' || $tag eq 'link') {
	    $berlinified .= $origtext;
	    return;
	}
	if (defined($attr->{'href'})) {
	    if ($attr->{'href'} !~ /^\s*http|^\s*mailto|$regex_url/) {
		$attr->{'href'} =~ s|^\s*(?:\.{0,2}/)*(.*)$|$new_query$base_url$1|;
	    } else {
		$attr->{'href'} = $new_query . $attr->{'href'}
	    }
	    $berlinified .= "<$tag ";
	    for(@$attrseq) {
		$berlinified .= $_ . qq(="$attr->{$_}" );
	    }
	    $berlinified .= ">";
	} elsif (defined($attr->{'src'})) {
	    if ($attr->{'src'} !~ /^\s*http|$regex_url/) {
		$attr->{'src'} =~ s|^\s*(?:\.{0,2}/)*(.*)$|$base_url$1|;
		$berlinified .= "<img ";
		for(@$attrseq) {
		    $berlinified .= $_ . qq(="$attr->{$_}" );
		}
		$berlinified .= ">";
	    }
	}
    }

    sub text {
	my ($self, $text) = @_;
	$text = substitute($text);
	$berlinified .= $text;
    }

    sub end {
	my ($self, $tag, $origtext) = @_;
	$berlinified .= $origtext;
    }
}
##### Package Berlinifyer end #####

use CGI qw(-no_xhtml);
my $q = new CGI;
my $url = undef;

my $rahoo_url = 'http://www.rahoo.de/';
my $css_url = $rahoo_url.'style/rahoostyle.css';
my $cgi_url = 'http://user.cs.tu-berlin.de/~ramiro/cgi-bin/berlinifyer.cgi';
my $outfile = undef;

# Security measures
$CGI::POST_MAX=1024*100;  # max 100 KBytes posts
$CGI::DISABLE_UPLOADS = 1;  # no uploads
$ENV{'PATH'} = '/bin:/usr/bin';
delete @ENV{'IFS','CDPATH','ENV','BASH_ENV'};

if ($q->param()) {
    my ($base_url,$regex_url) = undef;
    $url = $q->param('url');
    unless (($url =~ m|^(http://[\w.\@/~,\?&%\+=:-]+)$|i) && (length($url) > 11)) {
	slowdeath("<b>Der eingegebene URL wird von diesem Programm nich akzeptiert!</b>");
    }
    $url = $1; # untainted
	
    # Enable conversion of relative to full urls
    if ($url =~ m{^(.*/)\w+\.\w+\s*$}) { # e.g. (.*/)index.html
	$base_url = $1;
    } elsif ($url =~ m{^(http://.*?)/?\s*$}) {
	$base_url = $1.'/'; # append / after hostname
    } else {
	slowdeath("<b>Der eingegebene URL ist problematisch!</b>");
    }
    # Precompile RegEx to speed up program     
    $regex_url = qr($base_url);
	     
    # Get user document 
    use LWP::Simple;
    my $doc = get $url;
    
    # Instantiate Berlinifyer Object
    my $p = new Berlinifyer;
    $p->set_urls($regex_url,$base_url);
    $p->parse($doc);
    $p->eof(); # Clear buffer

    print $q->header();
    print $p->get_berlinified();
}
else {
    my $title = 'Rahoo - Berlinifyer';
    print $q->header(),$q->start_html({'title'=>$title,'author'=>'webmaster@rahoo.de','style'=>{'src'=>$css_url}});
    print $q->p('Hier k&ouml;nnen HTML-Dokumente ins Berlinische übersetzt werden. Bitte geben Sie die Internetadresse, des zu übersetzenden Dokuments an.'),
    $q->start_form({'method'=>'get'}),$q->textfield({'name'=>'url',
				    'size'=>'50',
				    'maxlength'=>'100',
				    'default'=>'http://'}),$q->submit(),
    $q->end_form(),$q->end_html();
}

# Handle incorrect input
# NOT YET FINISHED
sub slowdeath {
    my $message = shift;
    my $title = 'Fehler';
    print $q->header(),
    $q->start_html(-title=>"$title",
		   -style=>{'src' =>$css_url}),
    $q->p($message), $q->end_html;
    exit(1);
}
__END__
#### Todo list ####
Frames
use URI::URL ...
