#!/usr/bin/perl -wT
# Translate webpages to the dialect spoken in Berlin, Germany
# NAVBAR muss noch eingebaut werden auch in slowdeath
use strict;
use URI; # for absolutizing urls

# Globals
my $berlinified = undef; # String, where CGI-output is saved
my $new_query = "http://berlinifyer.sourceforge.net/cgi-bin/berlinifyer.cgi?url=";

# substitute words and letters
sub substitute {
    my $line = shift;
    my $vowel = 'aeiouäöü';
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

use CGI qw(-no_xhtml);
my $q = new CGI;

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
    my $url = $q->param('url');
    unless ( ($url =~ m|^((?:[^:/?#]+:)?(?://[^/?#]*)?[^?#]*(?:\?[^#]*)?(?:#.*)?)| )  && (length($url) > 11) ) {
	slowdeath("<b>Der eingegebene URL wird von diesem Programm nich akzeptiert!</b>");
    }
    $url = $1; # untainted

    # Create parser object
    use HTML::Parser;
    my $p = HTML::Parser->new( api_version => 3,
			       start_h => [\&start, "self, tag, attr, attrseq, text"],
			       text_h => [ \&text, "self, dtext" ],
			       end_h   => [\&end, "self, tag, text"]
			       #comment_h => [""],
			       );
    # Event handlers for HTML parser
    sub start {
	my ($self, $tag, $attr, $attrseq, $origtext) = @_;
	# Expand relative to full urls. Prepend $new_query to
	# webpage links, i.e. <a href="...">, so that linked pages
	# will be berlinified as well.
	# Applet and Object tags are currently ignored.
	
	# don't berlinify the contents of style tags
	if ($tag eq 'style') {
	    $self->{lasttag} = 1;
	    $berlinified .= $origtext;
	    return;
	}

	# handle scripts
	if ($tag eq 'script') {
	    if ( defined($attr->{'src'}) ) { # external
		my $abs_url = URI->new_abs($attr->{'src'}, $p->{base});
		$attr->{'src'} =~ s|$attr->{'src'}|$abs_url|;
		$berlinified .= "<$tag ";
		for(@$attrseq) {
		    $berlinified .= $_ . qq(="$attr->{$_}" );
		}
		$berlinified .= ">";
	    } else { # internal
		$self->{lasttag} = 1;
		$berlinified .= $origtext;
		return;
	    }
	} 
	
	# handle external style sheets
	if ($tag eq 'link') {
	    if (defined($attr->{'href'})) {
		my $abs_url = URI->new_abs($attr->{'href'}, $p->{base});
		$attr->{'href'} =~ s|$attr->{'href'}|$abs_url|;
		$berlinified .= "<$tag ";
		for(@$attrseq) {
		    $berlinified .= $_ . qq(="$attr->{$_}" );
		}
		$berlinified .= ">";
		return;
	    }
	}
	
	# handle links, images 
	if ($tag eq 'a' || $tag eq 'img') {
	    if (defined($attr->{'href'})) {
		my $abs_url = URI->new_abs($attr->{'href'}, $p->{base});
		my $new_url = $new_query . $abs_url;
		$attr->{'href'} =~ s|$attr->{'href'}|$new_url|;
	    } elsif (defined($attr->{'src'})) {
		my $abs_url = URI->new_abs($attr->{'src'}, $p->{base});
		$attr->{'src'} =~ s|$attr->{'src'}|$abs_url|;
	    }
	    $berlinified .= "<$tag ";
	    for(@$attrseq) {
		$berlinified .= $_ . qq(="$attr->{$_}" );
	    }
	    $berlinified .= ">";
	    return;
	} # if ($tag eq 'a' || $tag eq 'img')
	
        # all other tags
	else {
	    $berlinified .= $origtext;
	    return;
	}
    } # sub start

    sub text {
	my ($self, $text) = @_;
	if (defined($self->{lasttag})) {
	    $berlinified .= $text;
	    return;
	}
	$text = substitute($text);
	$berlinified .= $text;
    }

    sub end {
	my ($self, $tag, $origtext) = @_;
	$berlinified .= $origtext;
	if ($tag =~ m/style|script/) {
	    $self->{lasttag} = undef;
	}
    }

    # Get document and base url
    use LWP;
    my $doc;
    my $ua = LWP::UserAgent->new();
    my $request = HTTP::Request->new(GET => $url);
    my $response = $ua->request($request);
    if ($response->is_success) {
	$p->{base} = $response->base();
	$doc = $response->content();
    } else { slowdeath("URL $url could not be retrieved"); }
    
    # Parse HTML
    $p->parse($doc);
    $p->eof(); # Clear buffer

    print $q->header();
    print $berlinified;
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
