var e = 1024, t = 2048, n = 4096, r = 8192, i = 32768, a = 1 << 25, o = 65536, s = 1 << 19, c = 1 << 20, l = 1 << 25, u = 1 << 21, d = 1 << 22, f = 1 << 23, p = 1 << 27, m = 1 << 26, h = Symbol("$state"), g = Symbol("component"), _ = Symbol("legacy props"), v = Symbol(""), y = Symbol("attributes"), b = Symbol("class"), x = Symbol("style"), S = Symbol("text"), C = Symbol("form reset"), ee = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), te = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml"), ne = {}, w = Symbol("uninitialized");
function re() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function ie(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function ae() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
// node_modules/svelte/src/internal/client/dom/hydration.js
var T = !1;
function oe(e) {
	T = e;
}
var E;
function D(e) {
	if (e === null) throw ie(), ne;
	return E = e;
}
function se() {
	return D(/* @__PURE__ */ Ir(E));
}
function O(e) {
	if (T) {
		if (/* @__PURE__ */ Ir(E) !== null) throw ie(), ne;
		E = e;
	}
}
function ce(e = 1) {
	if (T) {
		for (var t = e, n = E; t--;) n = /* @__PURE__ */ Ir(n);
		E = n;
	}
}
function le(e = !0) {
	for (var t = 0, n = E;;) {
		if (Kr(n) === 8) {
			var r = ri(n) ?? "";
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r.startsWith("[?") || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ Ir(n);
		e && $r(n), n = i;
	}
}
function ue(e) {
	if (!e || Kr(e) !== 8) throw ie(), ne;
	return ri(e) ?? "";
}
// node_modules/svelte/src/internal/shared/utils.js
var de = Array.isArray, fe = Array.prototype.indexOf, pe = Array.prototype.includes, me = Array.from, he = Object.keys, ge = Object.defineProperty, _e = Object.getOwnPropertyDescriptor, ve = Object.getOwnPropertyDescriptors, ye = Object.prototype, be = Array.prototype, xe = Object.getPrototypeOf, Se = Object.isExtensible, Ce = () => {};
function we(e) {
	return e();
}
function Te(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function Ee() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
function De(e) {
	var t = U;
	if (t === null) return e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Oe(e, t);
}
function Oe(e, t) {
	if (e === ne) throw e;
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128 && !(t.f & 33570816)) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
function ke(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
function Ae(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function je(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Me() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function Ne(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Pe() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Fe() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Ie(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Le() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Re() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function ze() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Be() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
// node_modules/svelte/src/internal/flags/index.js
var Ve = !1;
function He() {
	Ve = !0;
}
// node_modules/svelte/src/internal/client/context.js
var k = null;
function Ue(e) {
	k = e;
}
function We(e, t = !1, n) {
	k = {
		p: k,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: U,
		l: Ve && !t ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ge(e) {
	var t = k, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) cn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, k = t.p, Ke(e);
}
function Ke(e = {}) {
	return ge(e, g, { value: !0 }), e;
}
function qe() {
	return !Ve || k !== null && k.l === null;
}
// node_modules/svelte/src/internal/client/dom/task.js
var Je = [];
function Ye() {
	var e = Je;
	Je = [], Te(e);
}
function Xe(e) {
	if (Je.length === 0 && !It) {
		var t = Je;
		queueMicrotask(() => {
			t === Je && Ye();
		});
	}
	Je.push(e);
}
function Ze() {
	for (; Je.length > 0;) Ye();
}
// node_modules/svelte/src/internal/client/reactivity/equality.js
function Qe(e) {
	return e === this.v;
}
function $e(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function et(e) {
	return !$e(e, this.v);
}
// node_modules/svelte/src/internal/client/custom-renderer/state.js
var tt = null;
// node_modules/svelte/src/internal/client/reactivity/async.js
function nt(e, t, n, r) {
	var i = U, a = t.map(qe() ? lt : pt), s = e.filter((e) => !e.settled);
	if (s.length > 0) {
		var c = rt(), l = ot();
		(s.length === 1 ? s[0].promise : Promise.all(s.map((e) => e.promise))).then(() => {
			if (!(i.f & 16384)) {
				c(s[0].run.get_batch());
				try {
					u();
				} catch (e) {
					Oe(e, i);
				}
				it();
			}
		}).finally(l);
	} else u();
	function u() {
		if (!e.some((e) => e.failed)) {
			if (n.length === 0) r(a);
			else {
				var t = n.map((e) => /* @__PURE__ */ dt(e)), s = null;
				gn(() => {
					for (var e of t) if (ft(e)) {
						q(e);
						return;
					}
					s === null ? s = z(() => {
						try {
							r([...a, ...t]);
						} catch (e) {
							Oe(e, i);
						}
					}) : F.revalidate_branch(s);
				}, o);
			}
		}
	}
}
function rt() {
	var e = U, t = V, n = k, r = F;
	return function(i = r) {
		Ln(e), H(t), Ue(n), i !== null && !(e.f & 16384) && A(i).activate();
	};
}
function it(e = !0) {
	Ln(null), H(null), Ue(null), e && F?.deactivate();
}
var at = null;
function ot() {
	for (var e = U, t = e.b, n = A(F), r = t; r && !r.is_pending;) r = r.parent;
	return n.increment(e), r?.increment(e, n), t?.update_effect_pending(1), () => {
		A(n).decrement(e), r?.decrement(e, n), t?.update_effect_pending(-1);
	};
}
function A(e) {
	for (; e.merged !== null;) e = e.merged;
	return e;
}
// node_modules/svelte/src/internal/client/reactivity/status.js
var st = ~(t | n | e);
function j(e, t) {
	e.f = e.f & st | t;
}
function ct(t) {
	t.f & 512 || t.edges === null ? j(t, e) : j(t, n);
}
/*#__NO_SIDE_EFFECTS__*/
function lt(e) {
	var n = 2 | t;
	return U !== null && (U.f |= s), {
		ctx: k,
		deps: null,
		dv: null,
		edges: null,
		effects: null,
		equals: Qe,
		f: n,
		fn: e,
		reactions: null,
		rv: 0,
		v: w,
		wv: 0,
		parent: U,
		ac: null
	};
}
var ut = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function dt(e, t, n, r) {
	var i = St(w);
	i.f |= d;
	var a = /* @__PURE__ */ new Set(), o = at, s = o && F, c = o && [];
	function l(e = !1) {
		var t = c;
		c = e ? null : [], e && (s = null);
		for (let e of t) e();
	}
	return pn(() => {
		var t = U, n = Ee();
		try {
			var u = e();
			if (u === w) return;
			var d = Promise.resolve(u), f = K?.signal;
			d.then((e) => {
				f?.aborted || n.resolve(e);
			}, (e) => {
				f?.aborted || e === ee && o === null || n.reject(e === ee ? ut : e);
			}).finally(it);
		} catch (e) {
			n.reject(e);
		}
		var p = F, m = ot();
		p.async_deriveds.get(t)?.reject(ut), a.add(n), p.async_deriveds.set(t, n);
		let h = (e, u = void 0) => {
			if (c !== null && u !== ut && (s ??= p, A(p) !== A(s))) c.push(() => {
				var r = !!(t.f & 16384) || (p.linked ? p.async_deriveds.get(t) !== n : !A(p).linked);
				h(e, r ? ut : u);
			});
			else {
				if (m(), a.delete(n), u) {
					if (c !== null && s !== null && (a.size > 0 || u === ut) && A(s) === A(p) && A(p).async_deriveds.get(t) === n) {
						s = null, l();
						return;
					}
					if (u === ut) return;
				}
				var d = i.equals(e) && !u && !(i.f & 8388608);
				A(p).capture(i, u ?? e, d, !!u), o !== null && (o.switch(p), o.continued.push(() => l(!0)), o = null), r?.(u), r = void 0;
			}
		};
		n.promise.then(h, (e) => h(null, e || "unknown"));
	}), on(() => {
		for (let e of a) e.reject(ut);
	}), i;
}
function ft(e) {
	return (L?.get(e) ?? e).v === w;
}
/*#__NO_SIDE_EFFECTS__*/
function pt(e) {
	let t = /* @__PURE__ */ lt(e);
	return t.equals = et, t;
}
function mt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function ht(e) {
	var t = U, n = e.parent;
	if (!Mn && n !== null && e.v !== w && n.f & 24576) return re(), ct(e), e.v;
	Ln(n);
	try {
		return mt(e), sr(e);
	} finally {
		Ln(t);
	}
}
function gt(e) {
	var t = e;
	if (Zn(t)) {
		var n = R?.records, r = n?.get(t);
		r !== void 0 && Jn(r.deps, r.dv) ? (n.delete(t), mr(t, r)) : ht(t);
	}
}
function _t(e) {
	var t = Nt, n = t.get(e);
	if (n !== void 0) return n;
	var r = R, i = L.get(e), a = i ?? e, o = i === void 0 ? (e.f & m) !== 0 : i.assigned, s = r.get_record(e);
	return o && !Yn((s ?? e).deps, a.wv) ? n = a : s !== void 0 && Jn(s.deps, s.dv) ? n = s : i === void 0 && !o && e.dv !== null && Jn(e.deps, e.dv) ? n = e : (ht(e), n = r.records?.get(e) ?? e), e.f & 512 && t.set(e, n), n;
}
function vt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.f & 134217728) && (t.teardown?.(), ar(t), t.fn !== null && (t.teardown = Ce), yr(t), vn(t));
}
function yt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && br(t);
}
// node_modules/svelte/src/internal/client/reactivity/sources.js
var bt = /* @__PURE__ */ new Set(), xt = !1;
function St(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Qe,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function Ct(e, t) {
	let n = St(e, t);
	return zn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function M(e, t = !1, n = !0) {
	let r = St(e);
	return t || (r.equals = et), Ve && n && k !== null && k.l !== null && (k.l.s ??= []).push(r), r;
}
function N(e, t, n = !1) {
	return V !== null && (!In || V.f & 131072) && qe() && V.f & 4325394 && (Rn === null || !Rn.has(e)) && ze(), wt(e, n ? Or(t) : t, Rt);
}
function wt(e, t, n = null) {
	var r = e.equals(t) && !(e.f & 8388608), i = L?.get(e);
	if (!r || i !== void 0 && (i.e || !e.equals.call(i, t))) {
		var a = Wt.ensure();
		(e.f & 67110914) == 2050 && ht(e), a.capture(e, t, r, !1, n), qe() && U !== null && U.f & 1024 && !(U.f & 96) && (Bn === null ? Vn([e]) : Bn.push(e));
	} else Mn && Mt(e);
	return t;
}
function Tt() {
	xt = !1, $t(Et);
}
function Et() {
	for (let e of bt) {
		e.f & 1024 && j(e, n);
		let t;
		try {
			t = Zn(e);
		} catch {
			t = !0;
		}
		t && br(e);
	}
	bt.clear();
}
function Dt(e) {
	N(e, e.v + 1);
}
// node_modules/svelte/src/internal/client/reactivity/batch.js
var P = null, Ot = null, F = null, kt = null, I = null;
function At(e) {
	I = e;
}
function jt(e) {
	var t = I = {
		reverted_values: new Map(I?.reverted_values),
		derived_cache: /* @__PURE__ */ new Map(),
		parent: I
	};
	for (let [n, r] of e ?? []) t.reverted_values.set(n, r);
	return t;
}
function Mt(e) {
	for (var t = I; t !== null; t = t.parent) t.reverted_values.delete(e), t.derived_cache.clear();
}
var L = null, Nt = null, R = null, Pt = null, Ft = /* @__PURE__ */ new Set(), It = !1, Lt = null, Rt = null, zt = 0, Bt = null, Vt = 0, Ht = 1, Ut = null, Wt = class r {
	id = Ht++;
	started = !1;
	linked = !0;
	prev = null;
	next = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	records = null;
	folded = [];
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = null;
	#i = /* @__PURE__ */ new Map();
	#a = [];
	#o = /* @__PURE__ */ new Set();
	#s = /* @__PURE__ */ new Set();
	is_fork = !1;
	merged = null;
	merge_requests = /* @__PURE__ */ new Set();
	#c = !1;
	constructor() {
		Ot === null ? P = Ot = this : (Ot.next = this, this.prev = Ot), Ot = this;
	}
	#l() {
		if (this.is_fork) return !0;
		for (let e of this.#n.keys()) if (this.is_blocked_by(e)) return !0;
		return !1;
	}
	#u(e) {
		return this.#o.has(e) || !!(e.f & 33554432) && !this.#s.has(e);
	}
	is_skipped(e) {
		for (var t = e; t !== null; t = t.parent) if (this.#u(t)) return !0;
		return !1;
	}
	is_blocked_by(e, t = null) {
		for (var n = e; n !== null && n !== t; n = n.parent) if (this.#u(n) || (n.f & 16512) == 128 && n.b.is_pending) return !1;
		return !0;
	}
	skip_effect(e) {
		this.#o.add(e), this.#s.delete(e);
	}
	unskip_effect(e) {
		(this.#o.delete(e) || !this.#s.has(e) && (e.f & 33554432 || this.folded.some((t) => t.#o.has(e)))) && this.revalidate_branch(e), this.#s.add(e);
	}
	unskip_new_effect(e) {
		this.#s.add(e);
	}
	revalidate_branch(e) {
		for (var t = e.first; t !== null; t = t.next) {
			var r = t.f;
			!(r & 24576) && !this.#u(t) && (!(r & 131168) && t.fn !== null && this.schedule(t, n), this.revalidate_branch(t));
		}
	}
	#d() {
		var t = [];
		for (let a of this.#a) if (!(a.f & 16384 || !(a.f & 6144))) {
			for (var n = a, r = !1; n.parent !== null;) {
				n = n.parent;
				var i = n.f;
				if (i & 96) {
					if (!(i & 1024)) {
						r = !0;
						break;
					}
					n.f ^= e;
				}
			}
			r || t.push(n);
		}
		return this.#a = [], t;
	}
	#f() {
		if (F = kt = this, I?.derived_cache.clear(), this.started = !0, Ut = this.id, this.#i.size > 0) {
			for (let [e, t] of this.#i) this.#S(e, t);
			this.#i.clear();
		}
		this.activate();
		for (var e = Lt = [], t = [], i = [], a = Rt = []; this.#a.length > 0;) {
			zt++ > 1e3 && (this.#T(), Kt());
			for (let n of this.#d()) try {
				this.#m(n, e, t, i);
			} catch (e) {
				throw en(n, !0), this.#l() || this.discard(), e;
			}
			if (this.#a.length > 0) {
				for (let e of t) this.#a.push(e);
				for (let t of e) this.#a.push(t);
				t.length = 0, e.length = 0;
			}
		}
		if (F = null, a.length > 0) {
			var o = r.ensure();
			for (let e of a) e.f & 1024 || o.schedule(e, n);
		}
		if (Lt = null, Rt = null, this.merge_requests.size > 0) {
			let n = Array.from(this.merge_requests, A).filter((e) => e !== this && e.linked && !e.is_fork).sort((e, t) => e.id - t.id);
			if (this.merge_requests.clear(), n.length > 0) {
				this.#y(t), this.#y(e);
				for (var s = this, c = n.length; c--;) {
					var l = n[c];
					l !== s && (l.#_(s), s = l);
				}
				s.#f();
				return;
			}
		}
		if (this.#l()) {
			this.#y(t), this.#y(e);
			for (let e of this.#o) en(e);
			a.length > 0 && F.#f();
			return;
		}
		let u = this.#h();
		if (u) this.#y(t), this.#y(e), u.#_(this), u.#f();
		else {
			for (let t of i) t.is_pending && t.is_ready(this) && t.reveal(e);
			this.#C(!0), this.#x(this.#e), Xt(e, Xt(t)), this.#r?.resolve();
			var d = F;
			if (this.#n.size === 0 && (this.#a.length === 0 || d !== null) && this.#T(), d !== null) {
				if (I !== null) for (let [e, t] of I.reverted_values) d.previous.get(e)?.wv !== t.wv && I.reverted_values.delete(e);
				d.#f();
			}
		}
	}
	#p(e) {
		var t = new Set(e), r = /* @__PURE__ */ new Set();
		for (let e of t) {
			var i = e.reactions;
			if (i !== null) for (let e of i) {
				var a = e.f;
				if (a & 2) a & 1024 && j(e, n), t.add(e);
				else {
					var o = e;
					r.has(o) || (r.add(o), !(a & 155648) && !this.is_skipped(o) && this.schedule(o, n));
				}
			}
		}
	}
	#m(t, n, r, i) {
		t.f ^= e;
		for (var a = t.first; a !== null;) {
			var o = a.f, s = !!(o & 96);
			if (!(s && o & 1024 || o & 139264 || this.#u(a)) && a.fn !== null) {
				s ? a.f ^= e : o & 4 ? n.push(a) : Zn(a) && br(a);
				var c = a.first;
				if (c !== null) {
					a = c;
					continue;
				}
			}
			for (; a !== null;) {
				if ((a.f & 16512) == 128) {
					var l = a.b;
					l.is_pending && l.is_ready(this) && i.push(l);
				}
				var u = a.next;
				if (u !== null) {
					a = u;
					break;
				}
				a = a.parent;
			}
		}
	}
	#h() {
		for (var e = this.prev; e !== null; e = e.prev) if (!e.is_fork && this.#g(e)) return e;
		return null;
	}
	#g(e) {
		for (let t of this.current.keys()) if (e.current.has(t)) return !0;
		return !1;
	}
	#_(e) {
		for (let t of e.merge_requests) this.merge_requests.add(t);
		e.merge_requests.clear();
		for (let [t, n] of e.current) {
			if (!this.previous.has(t)) {
				let n = e.previous.get(t);
				n && this.previous.set(t, n);
			}
			this.current.set(t, n);
		}
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && e !== n && n.promise.then(e.resolve, e.reject), this.async_deriveds.set(t, n);
		}
		for (let [n, r] of e.records ?? []) if (!(n.f & 16)) {
			var t = this.records?.get(n);
			(this.records ??= /* @__PURE__ */ new Map()).set(n, r), e.records?.delete(n), er(n, t);
		}
		if (e.async_deriveds.clear(), e.#n.size > 0) {
			for (let [t, n] of e.#n) this.#n.set(t, (this.#n.get(t) ?? 0) + n);
			e.#n.clear();
		}
		if (e.#i.size > 0) {
			for (let [t, n] of e.#i) this.#v(t, n);
			e.#i.clear();
		}
		let n = () => e.discard();
		this.oncommit(n), this.ondiscard(n), e.merged = this, e.#T();
	}
	#v(e, t) {
		(t === 2048 || this.#i.get(e) !== 2048) && this.#i.set(e, t);
	}
	#y(r) {
		for (var i = 0; i < r.length; i += 1) {
			var a = r[i], o = a.f & (t | n);
			o !== 0 && (this.#v(a, a.dv === null ? n : o), j(a, e));
		}
	}
	capture(e, n, r, i = !1, a = null) {
		var o = this.previous.get(e), s = Zt(this, e);
		o === void 0 && (o = s?.previous.get(e), o === void 0 && e.v !== w && (o = {
			v: e.v,
			wv: e.wv,
			e: (e.f & f) !== 0,
			assigned: (e.f & m) !== 0
		}), o !== void 0 && this.previous.set(e, o)), Mn ? Mt(e) : o !== void 0 && (I?.reverted_values.set(e, o), I?.derived_cache.clear());
		var c = {
			v: n,
			wv: r ? e.wv : Kn(),
			e: i,
			assigned: !!(e.f & 2),
			async: (e.f & d) !== 0
		};
		this.current.set(e, c), L?.set(e, c), Nt?.delete(e), !this.is_fork && s !== null && s.previous.set(e, c), !this.is_fork && !r && s === null && Qt(e, c), r || (Bt = null, Vt = 0, this.mark(e, t, a), Bt = null, bt.size > 0 && !xt && Tt());
	}
	deactivate() {
		F = kt = L = Nt = R = null;
	}
	flush() {
		var e = jt(this.previous);
		try {
			if (this.#f(), Ft.size > 0) for (let e of Ft) Ft.delete(e), e.linked && !e.#c && e.#f();
		} finally {
			zt = 0, Pt = null, Lt = null, Rt = null, I = e.parent, this.deactivate();
		}
	}
	discard() {
		this.#x(this.#t);
		for (let e of this.async_deriveds.values()) e.reject(ut);
		this.#T(), this.#r?.resolve();
	}
	#b() {
		for (let i = P; i !== null; i = i.next) if (i !== this) {
			var e = i.id < this.id, t = [];
			for (let [r, a] of this.current) {
				var n = i.current.get(r);
				if (n !== void 0) {
					if (e && a.v !== n.v && !n.async) i.current.set(r, a);
					else continue;
				}
				t.push(r);
			}
			if (i.started && i.current.size !== 0) {
				var r = !0;
				for (let e of i.current.keys()) if (!this.current.has(e)) {
					r = !1;
					break;
				}
				r && e ? i.discard() : t.length > 0 && (i.#p(t), Ft.add(i));
			}
		}
		this.current.clear(), this.previous.clear();
	}
	commit_writes() {
		this.#b(), this.linked && this.prev !== null && this.#w();
	}
	increment(e) {
		var t = this.#n.get(e) ?? 0;
		this.#n.set(e, t + 1);
	}
	decrement(e) {
		var t = this.#n.get(e) ?? 0;
		t === 1 ? this.#n.delete(e) : this.#n.set(e, t - 1), this.#c || (this.#c = !0, Xe(() => {
			this.#c = !1, this.linked && this.flush();
		}));
	}
	oncommit(e) {
		this.#e.set(e, Jt?.size ? Jt : null);
	}
	ondiscard(e) {
		this.#t.set(e, Jt?.size ? Jt : null);
	}
	#x(e) {
		J(() => {
			for (let [n, r] of e) if (r === null) n(this);
			else {
				var t = jt();
				for (let [e, n] of r) t.reverted_values.has(e) && t.reverted_values.set(e, n);
				try {
					n(this);
				} finally {
					I = t.parent;
				}
			}
		}), e.clear();
	}
	settled() {
		return (this.#r ??= Ee()).promise;
	}
	static ensure() {
		if (F === null) {
			let e = F = new r();
			kt === null && !It && Xe(() => {
				e.started || e.flush();
			});
		}
		return F;
	}
	activate() {
		F = this, R = this, Ut !== this.id && (Ut = null), L = Nt = null;
	}
	get_record(e) {
		for (var t = this.records?.get(e), n = this.folded.length; t === void 0 && n--;) t = this.folded[n].records?.get(e);
		return t;
	}
	mark(e, r, i = null) {
		var a = e.reactions;
		if (a !== null) {
			var o = qe(), s = a.length;
			if (Vt += s, Vt > 1e5 && Bt === null && (Bt = /* @__PURE__ */ new Set()), Bt !== null) {
				if (Bt.has(e)) return;
				Bt.add(e);
			}
			for (var c = 0; c < s; c++) {
				var l = a[c], u = l.f;
				if (o || l !== U) {
					var d = (u & t) === 0;
					if (u & 131072) this.is_fork || (d && j(l, r), bt.add(l));
					else if (u & 2) {
						d && j(l, r);
						var f = l;
						Nt?.delete(f), this.mark(f, n, i);
					} else if (d) {
						var p = l;
						u & 16 && qt !== null && (j(p, r), qt.add(p)), i === null ? this.schedule(p, r) : (j(p, r), i.push(p));
					}
				}
			}
		}
	}
	schedule(e, t) {
		if (Pt = e, R !== null && R !== this && e !== V) this.#v(e, e.f & 2097152 ? t : n);
		else {
			if (kt !== this && V === null) {
				if (this.prev !== null || this.next !== null || this.is_fork) {
					this.#v(e, n);
					return;
				}
				t = n;
			}
			this.#S(e, t);
		}
	}
	#S(e, t) {
		e.f & 2048 || j(e, t), this.#a.push(e);
	}
	#C(e = !1) {
		var t = this.records;
		if (t !== null) {
			this.records = null;
			for (let [r, i] of t) {
				if (!(r.f & 16386)) {
					var n = !!(r.f & 4194304) && rr(i) && !rr(r);
					if (e && !n && (mr(r, i), r.f & 4194304)) for (let e = P; e !== null; e = e.next) e !== this && !e.records?.has(r) && e.async_deriveds.get(r)?.reject(ut);
					gr(r);
				}
				er(r, i);
			}
		}
	}
	#w() {
		var e = this.prev, t = P;
		e.next = this.next, this.next === null ? Ot = e : this.next.prev = e, this.prev = null, this.next = t, t.prev = P = this, this.id = t.id - 1;
	}
	#T() {
		if (this.linked) {
			var e = this.prev, t = this.next;
			e === null ? P = t : e.next = t, t === null ? Ot = e : t.prev = e, this.linked = !1, this.#C();
		}
	}
};
function Gt(e) {
	var t = It, n = R === F ? null : R;
	It = !0;
	try {
		var r;
		for (e && (Gt(), r = e());;) {
			if (Ze(), F === null) return r;
			F.flush();
		}
	} finally {
		It = t, R = n;
	}
}
function Kt() {
	try {
		Pe();
	} catch (e) {
		Oe(e, Pt);
	}
}
var qt = null, Jt = null;
function Yt(e) {
	if ((e.f & 32772) != 4) return !1;
	for (var t = e.b; t !== null; t = t.parent) if (t.is_pending) return t.defer_effect(e), !0;
	return !1;
}
function Xt(e, t = null) {
	var n = e.length;
	if (n === 0) return t;
	for (var r = 0; r < n;) {
		var i = e[r++];
		if (!(i.f & 24576) && !F?.is_skipped(i) && !Yt(i) && Zn(i)) {
			qt = /* @__PURE__ */ new Set();
			var a = Hn;
			if (br(i), i.edges === null && i.first === null && i.nodes === null && i.teardown === null && i.ac === null && xn(i), qt?.size > 0) {
				var o = I;
				t !== null && jt(t);
				var s = Jt;
				Jt = new Map(t);
				try {
					for (let e of qt) {
						if (e.f & 24576 || F?.is_skipped(e)) continue;
						let t = [e], n = e.parent;
						for (; n !== null;) qt.has(n) && (qt.delete(n), t.push(n)), n = n.parent;
						for (let e = t.length - 1; e >= 0; e--) {
							let n = t[e];
							n.f & 24576 || F?.is_skipped(n) || br(n);
						}
					}
				} finally {
					Jt = s, qt?.clear(), I = o;
				}
			}
			if (Hn !== a && F !== null) for (let [e, n] of F.current) n.wv > a && (t ??= /* @__PURE__ */ new Map()).set(e, n);
		}
	}
	return qt = null, t;
}
function Zt(e, t) {
	for (var n = e.next; n !== null && (n.is_fork || !n.current.has(t));) n = n.next;
	return n;
}
function Qt(e, t) {
	e.v = t.v, e.wv = t.wv, e.f = t.e ? e.f | f : e.f & ~f, e.f & 2 && (e.f |= m, ct(e));
}
function $t(e) {
	var t = L, n = Nt, r = R;
	L = Nt = R = null;
	try {
		e();
	} finally {
		L = t, Nt = n, R = r;
	}
}
function en(t, n = !1) {
	if (!(!n && t.f & 32 && t.f & 1024)) {
		j(t, e);
		for (var r = t.first; r !== null;) en(r, n), r = r.next;
	}
}
// node_modules/svelte/src/internal/client/reactivity/effects.js
function tn(e) {
	U === null && (V === null && Ne(e), Me()), Mn && je(e);
}
function nn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function rn(e, n) {
	var i = U;
	i !== null && i.f & 8192 && (e |= r);
	var a = {
		ctx: k,
		deps: null,
		dv: null,
		edges: null,
		nodes: null,
		f: e | t | 512,
		first: null,
		fn: n,
		last: null,
		next: null,
		parent: i,
		b: i && i.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null,
		r: tt
	}, s = a;
	if (e & 4) Lt === null ? Wt.ensure().schedule(a, t) : Lt.push(a);
	else if (n !== null) {
		try {
			br(a);
		} catch (e) {
			throw B(a), e;
		}
		s.edges === null && s.teardown === null && s.nodes === null && s.first === s.last && !(s.f & 524288) && (s = s.first, e & 16 && e & 65536 && s !== null && (s.f |= o));
	}
	if (s !== null && (s.parent = i, i !== null && nn(s, i), V !== null && V.f & 2 && !(e & 64))) {
		var c = V;
		(c.effects ??= []).push(s);
	}
	return a;
}
function an() {
	return V !== null && !In;
}
function on(t) {
	let n = rn(8, null);
	return j(n, e), n.teardown = t, n;
}
function sn(e) {
	tn("$effect");
	var t = U.f;
	if (!V && t & 32 && k !== null && !k.i) {
		var n = k;
		(n.e ??= []).push(e);
	} else return cn(e);
}
function cn(e) {
	return rn(4 | c, e);
}
function ln(e) {
	return tn("$effect.pre"), rn(8 | c, e);
}
function un(e) {
	Wt.ensure();
	let t = rn(64 | s, e);
	return () => {
		B(t);
	};
}
function dn(e) {
	Wt.ensure();
	let t = rn(64 | s, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Sn(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function fn(e) {
	return rn(4, e);
}
function pn(e) {
	return rn(d | s, e);
}
function mn(e, t = 0) {
	return rn(8 | t, e);
}
function hn(e, t = [], n = [], r = []) {
	nt(r, t, n, (t) => {
		rn(8, () => {
			e(...t.map(q));
		});
	});
}
function gn(e, t = 0) {
	return rn(16 | t, e);
}
function z(e) {
	return rn(32 | s, e);
}
function _n(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = Mn, r = Nn, i = I, a = V;
		Pn(!0), H(null);
		try {
			t.call(null);
		} catch (t) {
			Oe(t, e.parent);
		} finally {
			Pn(n, r), At(i), H(a);
		}
	}
}
function vn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		ar(n);
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function yn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	try {
		(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (bn(e.nodes.start, e.nodes.end), n = !0), e.f |= a, vn(e, t && !n), yr(e);
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) e.stop();
		_n(e);
	} finally {}
	e.f ^= a, e.f |= 16384;
	var i = e.parent;
	i !== null && i.first !== null && xn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.dv = e.edges = e.fn = e.nodes = e.ac = e.b = e.r = null;
}
function bn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ Ir(e);
		$r(e), e = n;
	}
}
function xn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Sn(e, t, n = !0) {
	var r = [];
	e.f |= 256, Cn(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = I, s = () => {
			if (!--a) {
				var e = I;
				try {
					o && (o.derived_cache.clear(), At(o)), i();
				} finally {
					o && At(e);
				}
			}
		};
		for (var c of r) c.out(s);
	} else i();
}
function Cn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= r;
		var i = e.nodes && e.nodes.t;
		if (i !== null) for (let e of i) (e.is_global || n) && t.push(e);
		for (var a = e.first; a !== null;) {
			var o = a.next;
			if (!(a.f & 64)) {
				var s = !!(a.f & 65536) || !!(a.f & 32) && !!(e.f & 16);
				Cn(a, t, s ? n : !1);
			}
			a = o;
		}
	}
}
function wn(e) {
	e.f &= -257, Tn(e, !0);
}
function Tn(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= r, e.f & 1024 || Wt.ensure().schedule(e, n);
		for (var i = e.first; i !== null;) {
			var a = i.next, o = !!(i.f & 65536) || !!(i.f & 32);
			Tn(i, o ? t : !1), i = a;
		}
		var s = e.nodes && e.nodes.t;
		if (s !== null) for (let e of s) (e.is_global || t) && e.in();
	}
}
function En(e, t) {
	if (e.nodes) try {
		for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
			var i = n === r ? null : /* @__PURE__ */ Ir(n);
			Xr(t, n), n = i;
		}
	} finally {}
}
// node_modules/svelte/src/internal/client/legacy.js
var Dn = null, On = !1;
function kn() {
	On || (On = !0, di(document, "reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[C]?.();
		});
	}, { capture: !0 }));
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function An(e) {
	var t = V, n = U;
	H(null), Ln(null);
	try {
		return e();
	} finally {
		H(t), Ln(n);
	}
}
function jn(e, t, n, r = n) {
	e.addEventListener(t, () => An(n));
	let i = e[C];
	e[C] = i ? () => {
		i(), r(!0);
	} : () => r(!0), kn();
}
// node_modules/svelte/src/internal/client/runtime.js
var Mn = !1, Nn = 0;
function Pn(e, t = Hn) {
	Mn = e, Nn = t;
}
var Fn = {
	v: void 0,
	wv: 0,
	e: !1,
	assigned: !1
}, V = null, In = !1;
function H(e) {
	V = e;
}
var U = null;
function Ln(e) {
	U = e;
}
var Rn = null;
function zn(e) {
	V !== null && (V.f & 2097152 || V.f & 2) && (Rn ??= /* @__PURE__ */ new Set()).add(e);
}
var W = null, G = 0, Bn = null;
function Vn(e) {
	Bn = e;
}
var Hn = 1, Un = 0, Wn = Un;
function Gn(e) {
	Wn = e;
}
function Kn() {
	return ++Hn;
}
function qn(e) {
	return L === null ? (gt(e), e.wv) : e.f & 2 ? _t(e).wv : (L.get(e) ?? e).wv;
}
function Jn(e, t) {
	if (e !== null) {
		for (var n = 0; n < t.length; n++) if (qn(e[n]) !== t[n]) return !1;
	}
	return !0;
}
function Yn(e, t, n = null) {
	if (e !== null) for (var r = 0; r < e.length; r++) {
		var i = e[r];
		if (i.f & 2) {
			var a = i;
			if (L === null ? gt(i) : a = _t(i), a.wv > t) {
				if (a === i ? i.f & 67108864 : !("dv" in a)) return !0;
				if (n === null) n = /* @__PURE__ */ new Set();
				else if (n.has(a)) continue;
				if (Yn(a.deps, t, n)) return !0;
				n.add(a);
			}
		} else if (qn(i) > t) return !0;
	}
	return !1;
}
function Xn(e) {
	return !!(e.f & 4194320) && R?.get_record(e) || e;
}
function Zn(t) {
	var n = t.f;
	if (!(n & 6144)) return !1;
	if (n & 67108864) {
		if (Yn(t.deps, t.wv)) return !0;
	} else if (n & 2048) return !0;
	else {
		var r = Xn(t), i = r.deps, a = r.dv;
		if (a === null) return !0;
		if (L === null) for (var o = 0, s = a.length; o < s; o++) {
			var c = i[o];
			if (gt(c), c.wv !== a[o]) return !0;
		}
		else if (!Jn(i, a)) return !0;
	}
	return n & 512 && j(t, e), !1;
}
function Qn(e, r, i = !0) {
	var a = e.reactions;
	if (a !== null && !(Rn !== null && Rn.has(e))) for (var o = 0; o < a.length; o++) {
		var s = a[o];
		s.f & 2 ? Qn(s, r, !1) : r === s && F.schedule(s, i ? t : n);
	}
}
var K = null;
function $n(e) {
	e && An(() => e.abort(ee));
}
function er(e, t, n = !1) {
	if (t?.ac) {
		for (var r = P; r !== null; r = r.next) if (r.records?.get(e) === t && (!n || r !== R && !ir(F, r))) return;
		$n(t.ac), t.ac = null;
	}
}
function tr(e, t) {
	var n = F, r = !!(t & 2);
	if (!(r && Mn)) {
		var i = n === null || !n.is_fork;
		er(e, R?.records?.get(e), !0), (r ? L === null || i && rr(e) : i) && $n(e.ac);
		for (var a = P; a !== null; a = a.next) ir(n, a) && er(e, a.records?.get(e), !0);
	}
}
function nr(e) {
	$n(e.ac), e.ac = K;
}
function rr({ deps: e, dv: t }) {
	return t === null || t.some((t, n) => e[n].wv !== t);
}
function ir(e, t) {
	return e !== null && !e.is_fork && !t.is_fork && t.id < e.id && (L === null || t.previous.size === 0 || e.folded.includes(t));
}
function ar(e) {
	if (!(e.f & 134217728)) return !1;
	e.f ^= p, $n(e.ac), e.ac = null;
	for (var t = P; t !== null; t = t.next) {
		var n = t.records?.get(e);
		n?.ac && ($n(n.ac), n.ac = null);
	}
	return !0;
}
function or(e) {
	return !(e & 4194304) && (e & 32784) != 32784 ? !1 : R !== null && R === F;
}
function sr(e) {
	let t = F;
	var n = W, r = G, a = Bn, o = V, s = Rn, c = k, l = In, d = Wn, f = e.f;
	W = null, G = 0, Bn = null, V = f & 96 ? null : e, Rn = null, Ue(e.ctx), In = !1, Wn = ++Un;
	var p = K;
	K = null, f & 134217728 && tr(e, f);
	try {
		e.f |= u;
		var m = e.fn, h = m();
		if (e.f |= i, cr(e, f, h, !1), qe() && Bn !== null && !In && (W !== null || G > 0) && !(e.f & 6146)) for (var g = 0; g < Bn.length; g++) Qn(Bn[g], e);
		if (o !== null && o !== e) {
			if (Un++, o.deps !== null) for (let e = 0; e < r; e += 1) o.deps[e].rv = Un;
			if (n !== null) for (let e of n) e.rv = Un;
			Bn !== null && (a === null ? a = Bn : a.push(...Bn));
		}
		return h;
	} catch (t) {
		var _ = t;
		try {
			_ = De(t);
		} finally {
			cr(e, f, _, _ === t);
		}
		return _;
	} finally {
		var v = K?.signal;
		t !== null && v !== void 0 && v.addEventListener("abort", () => {
			if (F !== null) {
				let e = A(t);
				e !== F && e.linked && !e.is_fork && F.merge_requests.add(e);
			}
		}), e.f ^= u, W = n, G = r, Bn = a, V = o, Rn = s, Ue(c), In = l, Wn = d, K = p;
	}
}
function cr(e, t, n, r) {
	var i = e.deps, a = G + (W === null ? 0 : W.length), o = e.dv;
	if (e.f & 16384) $n(K);
	else if (K !== null && !(e.f & 134217728) && ($n(K), K = null), t & 2 && Mn) {
		for (var s = 0, c = 0; c < a; c++) {
			var l = c < G ? i[c] : W[c - G];
			s = Math.max(s, Tr(l));
		}
		Fn = {
			v: n,
			wv: s,
			e: r,
			assigned: (t & m) !== 0
		};
	} else if (t & 2 && L === null && P !== null && P.next !== null && dr(e, t), W === null && L === null && o !== null && a === i?.length && e.edges === i && !(t & 4194320)) {
		for (var u = 0; u < a; u++) o[u] = i[u].wv;
		o.length !== a && (o.length = a), t & 2 && lr(e, n, r), (e.ac || K) && nr(e);
	} else ur(e, t, a, n, r);
}
function lr(e, t, n) {
	var r = e.f & ~m;
	(n || r & 8388608 || !e.equals(t)) && (e.v = t, e.wv = Kn(), r = n ? r | f : r & ~f), e.f = r, ct(e);
}
function ur(e, t, n, r, i) {
	var a = or(t);
	if (L !== null && t & 2) {
		var o = L.get(e);
		o !== void 0 && o.wv !== e.wv && (a = !0);
	}
	var s = e.deps, c = s;
	(W !== null || G !== s?.length) && (c = G === 0 ? W : s.slice(0, G).concat(W ?? []));
	for (var l = !a && L === null && e.dv !== null ? e.dv : [], u = 0; u < n; u++) {
		var d = c[u];
		l[u] = fr(d), L !== null && t & 2 && (l[u] !== d.wv || (d.f & 1026) == 2) && (a = !0);
	}
	l.length !== n && (l.length = n), !a && L !== null && t & 2 && dr(e, t);
	var f = a || hr(e), p = an() && !!(e.f & 512), m = e.edges;
	if (f && m !== null) {
		if (W !== null) {
			e.edges = m = m.slice();
			for (d of W) pe.call(m, d) || (m.push(d), p && (d.reactions ??= []).push(e));
		}
	} else {
		if (m === s) {
			if (m !== null) for (u = G; u < m.length; u++) vr(e, m[u]);
			if (p && W !== null) for (d of W) (d.reactions ??= []).push(e);
		} else {
			var h = new Set(c);
			for (d of m) h.delete(d) || vr(e, d);
			if (p) for (d of h) (d.reactions ??= []).push(e);
		}
		e.edges = c;
	}
	if (a) {
		var g = R;
		(g.records ??= /* @__PURE__ */ new Map()).set(e, t & 2 ? {
			deps: c,
			dv: l,
			v: r,
			e: i,
			wv: pr(e, g, r, i),
			ac: K
		} : {
			deps: c,
			dv: l,
			ac: K
		});
	} else e.deps = c, e.dv = l, (e.ac || K) && nr(e), t & 2 && (lr(e, r, i), R?.records?.delete(e));
}
function dr(e, t) {
	var n = e.dv;
	if (!(n === null || n.length === 0 || t & 67108864)) {
		for (var r, i = e.ac, a = i !== null && F !== null && F.is_fork && !i.signal.aborted, o = P; o !== null; o = o.next) o !== R && !o.records?.has(e) && (i === null || a || ir(F, o)) && (r ??= {
			deps: e.deps,
			dv: n.slice(),
			v: e.v,
			wv: e.wv,
			e: (t & f) !== 0
		}, (o.records ??= /* @__PURE__ */ new Map()).set(e, r));
		a && r !== void 0 && (r.ac = i, e.ac = null);
	}
}
function fr(e) {
	return L === null ? e.wv : e.f & 2 ? Nt.get(e)?.wv ?? -1 : (L.get(e) ?? e).wv;
}
function pr(e, t, n, r) {
	if (!r) {
		var i = t.get_record(e);
		if (i !== void 0 && !i.e && e.equals.call(i, n)) return i.wv;
		if (!(e.f & 8388608) && e.equals(n)) return e.wv;
	}
	return Kn();
}
function mr(e, t) {
	if (e.deps = t.deps, e.dv = e.f & 2 ? t.dv.slice() : t.dv, e.f & 2) {
		var n = e;
		n.v = t.v, n.wv = t.wv, n.f = (t.e ? n.f | f : n.f & ~f) & ~m, ct(n);
	}
	$n(e.ac), e.ac = t.ac ?? null, t.ac = null;
}
function hr(e) {
	for (var t = P; t !== null; t = t.next) if (t.records?.has(e)) return !0;
	return !1;
}
function gr(e) {
	var t = e.edges, n = e.deps;
	if (!(t === n || hr(e))) {
		for (var r of t) n !== null && pe.call(n, r) || vr(e, r);
		e.edges = n;
	}
}
function _r(e, t) {
	var n = e.reactions ??= [];
	pe.call(n, t) || n.push(t);
}
function vr(e, n) {
	let r = n.reactions;
	if (r !== null) {
		var i = fe.call(r, e);
		if (i !== -1) {
			var a = r.length - 1;
			a === 0 ? r = n.reactions = null : (r[i] = r[a], r.pop());
		}
	}
	if (r === null && n.f & 2 && (W === null || !pe.call(W, n))) {
		var o = n;
		if (o.f & 512 && (o.f ^= 512), o.v !== w && ct(o), ar(o)) {
			j(o, t), o.dv = null;
			for (var s = P; s !== null; s = s.next) s.records?.delete(o);
			Nt?.delete(o);
		}
		vt(o), yr(o);
	}
}
function yr(e) {
	var t = e.edges;
	if (t !== null) for (var n = 0; n < t.length; n++) vr(e, t[n]);
}
function br(t) {
	var n = t.f;
	if (!(n & 16384)) {
		j(t, e);
		var r = U;
		U = t;
		try {
			n & 16777232 ? yn(t) : vn(t), _n(t);
			var i = sr(t);
			t.teardown = typeof i == "function" ? i : null, t.wv = Hn;
		} finally {
			U = r;
		}
	}
}
async function xr() {
	await Promise.resolve(), Gt();
}
function q(e) {
	var t = !!(e.f & 2);
	Dn?.add(e);
	var n = null;
	if (V !== null && !In && !(U !== null && U.f & 16384) && (Rn === null || !Rn.has(e))) {
		var r = V.deps;
		if (V.f & 2097152) e.rv < Un && (e.rv = Un, W === null && r !== null && r[G] === e ? G++ : W === null ? W = [e] : W.push(e));
		else {
			n = V;
			var a = V.edges;
			a !== null && pe.call(a, e) || (V.edges = a === null ? [e] : [...a, e]), _r(e, V);
		}
	}
	if (Mn) {
		var o = wr(e);
		if (o !== void 0) {
			if (o.e) throw o.v;
			return o.v;
		}
	}
	var s;
	if (t) {
		var c = e, l = !(c.f & 512) && !In && V !== null && !!(V.f & 512), u = !(c.f & i);
		l && (c.f |= 512), L === null ? gt(c) : s = _t(c), l && !u && (yt(c), Cr(c));
	} else L !== null && (s = L.get(e));
	if (n !== null && Sr(n, e, s === void 0 ? e.wv : s.wv), s !== void 0 && s !== e) {
		if (s.e) throw s.v;
		return s.v;
	}
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function Sr(e, t, n) {
	var r = Xn(e), i = r.deps;
	r.dv === null || i !== null && pe.call(i, t) || (r.deps = i === null ? [t] : [...i, t], r.dv.push(n));
}
function Cr(e) {
	if (e.f |= 512, e.edges !== null) for (let t of e.edges) _r(t, e), t.f & 2 && !(t.f & 512) && (yt(t), Cr(t));
}
function wr(e) {
	var t = e.wv > Nn ? void 0 : I?.reverted_values.get(e);
	if (!(e.f & 2)) return t;
	var n = e, r = (I ?? jt()).derived_cache, i = r.get(n);
	if (i !== void 0) return i;
	var a = t ?? L?.get(n), o = a === void 0 ? (n.f & m) !== 0 : a.assigned, s = a === void 0 && !o ? n.dv : null, c = n.deps ?? [], l = o || s !== null, u = s?.length ?? c.length;
	a ??= {
		v: n.v,
		wv: n.wv,
		e: (n.f & f) !== 0,
		assigned: (n.f & m) !== 0
	};
	for (var d = 0; l && d < u; d++) {
		var p = Tr(c[d]);
		l = s === null ? p <= a.wv : p === s[d];
	}
	return l ? i = a : (ht(n), i = Fn, a.wv < i.wv && !a.e && !i.e && n.equals.call(a, i.v) && (i.wv = a.wv)), r.set(n, i), i;
}
function Tr(e) {
	return (wr(e) ?? L?.get(e) ?? e).wv;
}
function J(e) {
	var t = In;
	try {
		return In = !0, e();
	} finally {
		In = t;
	}
}
function Er(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (h in e) Dr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && h in n && Dr(n);
		}
	}
}
function Dr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			Dr(e[n], t);
		} catch {}
		let n = xe(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = ve(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
function Or(e) {
	if (typeof e != "object" || !e || h in e || g in e) return e;
	let t = xe(e);
	if (t !== ye && t !== be) return e;
	var n = /* @__PURE__ */ new Map(), r = de(e), i = /* @__PURE__ */ Ct(0), a = null, o = Wn, s = (e) => {
		if (Wn === o) return e();
		var t = V, n = Wn;
		H(null), Gn(o);
		var r = e();
		return H(t), Gn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Ct(e.length, a)), new Proxy(e, {
		defineProperty(e, t, r) {
			"value" in r && r.configurable !== !1 && r.enumerable !== !1 && r.writable !== !1 || Le();
			var i = n.get(t);
			return i === void 0 ? s(() => {
				var e = /* @__PURE__ */ Ct(r.value, a);
				return n.set(t, e), e;
			}) : N(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = s(() => /* @__PURE__ */ Ct(w, a));
					n.set(t, e), Dt(i);
				}
			} else N(r, w), Dt(i);
			return !0;
		},
		get(t, r, i) {
			if (r === h) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || _e(t, r)?.writable) && (o = s(() => /* @__PURE__ */ Ct(Or(c ? t[r] : w), a)), n.set(r, o)), o !== void 0) {
				var l = q(o);
				return l === w ? void 0 : l;
			}
			return Reflect.get(t, r, i);
		},
		getOwnPropertyDescriptor(e, t) {
			this.has?.(e, t);
			var r = Reflect.getOwnPropertyDescriptor(e, t), i = n.get(t);
			if (i !== void 0) {
				var a = q(i);
				if (a === w) return;
				if (r && "value" in r) r.value = a;
				else return {
					enumerable: !0,
					configurable: !0,
					value: a,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === h) return !0;
			var r = n.get(t), i = r !== void 0 && r.v !== w || Reflect.has(e, t);
			return (r !== void 0 || (U !== null || V !== null) && (!i || _e(e, t)?.writable)) && (r === void 0 && (r = s(() => /* @__PURE__ */ Ct(i ? Or(e[t]) : w, a)), n.set(t, r)), q(r) === w) ? !1 : i;
		},
		set(e, t, o, c) {
			var l = n.get(t), u = t in e;
			if (r && t === "length") for (var d = o; d < l.v; d += 1) {
				var f = n.get(d + "");
				f === void 0 ? d in e && (f = s(() => /* @__PURE__ */ Ct(w, a)), n.set(d + "", f)) : N(f, w);
			}
			if (l === void 0) (!u || _e(e, t)?.writable) && (l = s(() => /* @__PURE__ */ Ct(void 0, a)), N(l, Or(o)), n.set(t, l));
			else {
				u = l.v !== w;
				var p = s(() => Or(o));
				N(l, p);
			}
			var m = Reflect.getOwnPropertyDescriptor(e, t);
			if (m?.set && m.set.call(c, o), !u) {
				if (r && typeof t == "string") {
					var h = n.get("length"), g = Number(t);
					Number.isInteger(g) && g >= h.v && N(h, g + 1);
				}
				Dt(i);
			}
			return !0;
		},
		ownKeys(e) {
			q(i);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== w;
			});
			for (var [r, a] of n) a.v !== w && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Re();
		}
	});
}
var kr, Ar, jr, Mr;
function Nr() {
	if (kr === void 0) {
		kr = window, Ar = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		jr = _e(t, "firstChild").get, Mr = _e(t, "nextSibling").get, Se(e) && (e[b] = void 0, e[y] = null, e[x] = void 0, e.__e = void 0), Se(n) && (n[S] = void 0);
	}
}
function Pr(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function Fr(e) {
	return jr.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function Ir(e) {
	return Mr.call(e);
}
function Y(e, t) {
	if (!T) return /* @__PURE__ */ Fr(e);
	var n = /* @__PURE__ */ Fr(E);
	if (n === null) n = Xr(E, Pr());
	else if (t && Kr(n) !== 3) {
		var r = Pr();
		return Zr(n, r), D(r), r;
	}
	return t && Wr(n), D(n), n;
}
function Lr(e, t = !1) {
	if (!T) {
		var n = /* @__PURE__ */ Fr(e);
		return Gr(n) && ri(n) === "" ? /* @__PURE__ */ Ir(n) : n;
	}
	if (t) {
		if (Kr(E) !== 3) {
			var r = Pr();
			return E && Zr(E, r), D(r), r;
		}
		Wr(E);
	}
	return E;
}
function Rr(e, t = !1) {
	if (!T) return /* @__PURE__ */ Fr(e);
	var n = Y(e, t);
	return O(e), n;
}
function X(e, t = 1, n = !1) {
	let r = T ? E : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ Ir(r);
	if (!T) return r;
	if (n) {
		if (Kr(r) !== 3) {
			var a = Pr();
			return r === null ? i && Qr(i, a) : Zr(r, a), D(a), a;
		}
		Wr(r);
	}
	return D(r), r;
}
function zr(e) {
	e.textContent = "";
}
function Br() {
	return Jt !== null && !!(U.f & i);
}
function Vr(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function Hr() {
	return document.createDocumentFragment();
}
function Ur(e, t, n = "") {
	if (t.startsWith("xlink:")) e.setAttributeNS("http://www.w3.org/1999/xlink", t, n);
	else return e.setAttribute(t, n);
}
function Wr(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && Kr(t) === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function Gr(e) {
	return e instanceof Comment;
}
function Kr(e) {
	if (e != null) return e.nodeType;
}
function qr(e) {
	return e.nodeName;
}
function Jr(e) {
	return e.lastChild;
}
function Yr(e) {
	return e.parentNode;
}
function Xr(e, t) {
	return e.appendChild(t);
}
function Zr(e, t) {
	e.before(t);
}
function Qr(e, t) {
	e.after(t);
}
function $r(e) {
	e.remove();
}
function ei(e, t) {
	return e.removeChild(t);
}
function ti(e, t) {
	e.textContent = t;
}
function ni(e, t) {
	e.nodeValue = t;
}
function ri(e) {
	return e.nodeValue;
}
function ii(e, t) {
	e.value = t ?? "";
}
function ai(e, t) {
	return e.getAttribute(t);
}
function oi(e, t) {
	e.removeAttribute(t);
}
function si(e, t) {
	return e.hasAttribute(t);
}
function ci(e, t) {
	e.innerHTML = t;
}
function li(e, t) {
	return e.cloneNode(t);
}
function ui(e, t) {
	return document.importNode(e, t);
}
function di(e, t, n, r) {
	e.addEventListener(t, n, r);
}
function fi(e, t, n, r) {
	e.removeEventListener(t, n, r);
}
function pi(e, t, n) {
	e.classList.toggle(t, n);
}
// node_modules/svelte/src/internal/flags/legacy.js
Nr(), typeof window < "u" && ((globalThis.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5"), He(), [.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var mi = ["touchstart", "touchmove"];
function hi(e) {
	return mi.includes(e);
}
// node_modules/svelte/src/internal/client/dom/elements/events.js
var gi = Symbol("events"), _i = Symbol("propagation stopped at"), vi = /* @__PURE__ */ new Set(), yi = /* @__PURE__ */ new Set();
function bi(e, t, n, r = {}) {
	var i = tt != null;
	function a(...e) {
		if (i) return An(() => n?.apply(this, e));
		var a = e[0];
		if (r.capture || Ti.call(t, a), r.capture || a[_i] !== t) return An(() => n?.call(this, a));
	}
	return !i && (e.startsWith("pointer") || e.startsWith("touch") || e === "wheel") ? (a.__removed = !1, Xe(() => {
		a.__removed || di(t, e, a, r);
	})) : di(t, e, a, r), a;
}
function Z(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = bi(e, t, n, a);
	tt == null && (t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && on(() => {
		o.__removed = !0, fi(t, e, o, a);
	});
}
var xi = /* @__PURE__ */ new Map();
function Si(e) {
	var t = /* @__PURE__ */ new Set(), n = (n) => {
		for (var r = 0; r < n.length; r++) {
			var i = n[r];
			if (!t.has(i)) {
				t.add(i);
				var a = hi(i);
				for (let t of [e, document]) {
					var o = xi.get(t);
					o === void 0 && (o = /* @__PURE__ */ new Map(), xi.set(t, o));
					var s = o.get(i);
					s === void 0 ? (t.addEventListener(i, Ti, { passive: a }), o.set(i, 1)) : o.set(i, s + 1);
				}
			}
		}
	};
	return n(me(vi)), yi.add(n), () => {
		for (var r of t) for (let t of [e, document]) {
			var i = xi.get(t), a = i.get(r);
			--a == 0 ? (t.removeEventListener(r, Ti), i.delete(r), i.size === 0 && xi.delete(t)) : i.set(r, a);
		}
		yi.delete(n);
	};
}
var Ci = null, wi = !1;
function Ti(e) {
	var t = this, n = e.cancelBubble;
	if (!(n && e[_i] === t)) {
		n || delete e[_i];
		var r = t.ownerDocument, i = e.type, a = e.composedPath?.() || [], o = a[0] || e.target;
		Ci = e, wi || (wi = !0, setTimeout(() => {
			wi = !1, Ci = null;
		}));
		var s = 0, c = Ci === e && e[gi];
		if (c) {
			var l = a.indexOf(c);
			if (l !== -1 && (t === document || t === window)) {
				e[gi] = t;
				return;
			}
			var u = a.indexOf(t);
			if (u === -1) return;
			l <= u && (s = l);
		}
		if (o = a[s] || e.target, o !== t) {
			ge(e, "currentTarget", {
				configurable: !0,
				get() {
					return o || r;
				}
			});
			var d = V, f = U;
			H(null), Ln(null);
			try {
				for (var p, m = []; o !== null && o !== t;) {
					try {
						var h = o[gi]?.[i];
						h == null || o.disabled && e.target !== o || h.call(o, e);
					} catch (e) {
						p ? m.push(e) : p = e;
					}
					if (e.cancelBubble) {
						n || (e[_i] = t);
						break;
					}
					s++, o = s < a.length ? a[s] : null;
				}
				if (p) {
					for (let e of m) queueMicrotask(() => {
						throw e;
					});
					throw p;
				}
			} finally {
				e[gi] = t, delete e.currentTarget, H(d), Ln(f);
			}
		}
	}
}
// node_modules/svelte/src/internal/client/dom/reconciler.js
var Ei = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function Di(e) {
	return Ei?.createHTML(e) ?? e;
}
function Oi(e) {
	var t = Vr("template");
	return ci(t, Di(e.replaceAll("<!>", "<!---->"))), t.content;
}
// node_modules/svelte/src/internal/client/dom/template.js
function ki(e, t) {
	var n = U;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Q(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (T) return ki(E, null), E;
		i === void 0 && (i = Oi(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ Fr(i)));
		var t = r || Ar ? ui(i, !0) : li(i, !0);
		return n ? ki(/* @__PURE__ */ Fr(t), Jr(t)) : ki(t, t), t;
	};
}
function $(e, t) {
	if (T) {
		var n = U;
		n.f & 32768 && n.nodes.end !== null || (n.nodes.end = E), se();
	} else e !== null && Zr(e, t);
}
// node_modules/svelte/src/reactivity/create-subscriber.js
function Ai(e) {
	let t = 0, n = St(0), r;
	return () => {
		an() && (q(n), mn(() => (t === 0 && (r = J(() => e(() => Dt(n)))), t += 1, () => {
			Xe(() => {
				--t, t === 0 && (r?.(), r = void 0, Dt(n));
			});
		})));
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var ji = o | s;
function Mi(e, t, n, r) {
	new Ni(e, t, n, r);
}
var Ni = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = T ? E : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = !1;
	#d = [];
	#f = /* @__PURE__ */ new Map();
	#p = null;
	#m = Ai(() => (this.#p = St(this.#l), () => {
		this.#p = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = U;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = U.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = gn(() => {
			if (T) {
				let e = ue(this.#t);
				se();
				let t = e === "[!";
				if (e.startsWith("[?")) {
					let t = JSON.parse(e.slice(2));
					this.#g(t);
				} else t ? this.#y() : this.#h();
			} else this.#b();
		}, ji), T && (this.#e = E);
	}
	#h() {
		try {
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#g(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#_(e);
		Xe(r), t && (this.#s = z(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#_(e) {
		var t = !1, n = !1;
		let r = () => {
			this.#v() || (t ? ae() : (t = !0, n && Be(), this.#s !== null && Sn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#b();
			})));
		};
		return {
			reset: r,
			invoke_onerror: () => {
				if (!this.#v()) try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					Oe(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#v() {
		return !!(this.#i.f & 33570816);
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), Xe(() => {
			if (!this.#v()) try {
				var e = this.#c = Hr(), t = Pr();
				Xr(e, t), this.#a = this.#x(() => {
					try {
						return z(() => this.#r(t));
					} catch (e) {
						try {
							this.error(e);
						} catch (e) {
							Oe(e, this.#i.parent);
						}
						return null;
					}
				}), this.#a !== null && this.#f.size === 0 && (this.is_pending = !1, Zr(this.#e, e), this.#c = null, Sn(this.#o, () => {
					this.#o = null;
				}));
			} finally {}
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#f.size === 0) this.is_pending = !1;
			else {
				let t = this.#n.pending;
				if (t) {
					var e = this.#c = Hr();
					En(this.#a, e), this.#o = z(() => t(this.#e));
				}
			}
		} catch (e) {
			this.error(e);
		}
	}
	defer_effect(e) {
		this.#d.push(e);
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = U, n = V, r = k;
		Ln(this.#i), H(this.#i), Ue(this.#i.ctx);
		try {
			return Wt.ensure(), e();
		} finally {
			Ln(t), H(n), Ue(r);
		}
	}
	is_ready(e) {
		if (e.is_fork && this.#f.size > 0) return !1;
		for (let [t, n] of this.#f) if (!t.is_fork) {
			for (let t of n.keys()) if (e.is_blocked_by(t, this.#a)) return !1;
		}
		return !0;
	}
	reveal(e) {
		this.is_pending = !1;
		for (let n of this.#d) j(n, t), e.push(n);
		if (this.#d.length = 0, this.#o && Sn(this.#o, () => {
			this.#o = null;
		}), this.#c) try {
			Zr(this.#e, this.#c), this.#c = null;
		} finally {}
	}
	increment(e, t) {
		var n = this.#f.get(t);
		n === void 0 && this.#f.set(t, n = /* @__PURE__ */ new Map());
		var r = n.get(e) ?? 0;
		n.set(e, r + 1);
	}
	decrement(e, t) {
		var r = this.#f.get(t), i = r.get(e);
		i === 1 ? (r.delete(e), r.size === 0 && this.#f.delete(t), Xe(() => {
			this.is_pending && !this.#v() && Wt.ensure().schedule(this.#i, n);
		})) : r.set(e, i - 1);
	}
	update_effect_pending(e) {
		this.#l += e, !this.#p || this.#u || (this.#u = !0, Xe(() => {
			this.#u = !1, this.#p && wt(this.#p, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#m(), q(this.#p);
	}
	error(e) {
		if (e === ne || !this.#n.onerror && !this.#n.failed) throw e;
		F?.is_fork ? (this.#a && F.skip_effect(this.#a), this.#o && F.skip_effect(this.#o), this.#s && F.skip_effect(this.#s), F.oncommit(() => {
			this.#v() || this.#S(e);
		})) : this.#S(e);
	}
	#S(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), T && (D(this.#t), ce(), D(le()));
		let t = this.#n.failed, n = (e) => {
			if (this.#v()) return;
			let { reset: n, invoke_onerror: r } = this.#_(e);
			r(), t && !this.#v() && (this.#s = this.#x(() => {
				try {
					return z(() => {
						var r = U;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return Oe(e, this.#i.parent), null;
				}
			}));
		};
		Xe(() => {
			if (!this.#v()) {
				var t;
				try {
					t = this.transform_error(e);
				} catch (e) {
					Oe(e, this.#i && this.#i.parent);
					return;
				}
				typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => Oe(e, this.#i && this.#i.parent)) : n(t);
			}
		});
	}
};
function Pi(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[S] ??= ri(e)) && (e[S] = n, ni(e, `${n}`));
}
function Fi(e, t) {
	return Li(e, t);
}
function Ii(e, t) {
	t.intro = t.intro ?? !1;
	let n = t.target, r = T, i = E;
	try {
		for (var a = /* @__PURE__ */ Fr(n); a && (Kr(a) !== 8 || ri(a) !== "[");) a = /* @__PURE__ */ Ir(a);
		if (!a) throw ne;
		oe(!0), D(a);
		let r = Li(e, {
			...t,
			anchor: a
		});
		return oe(!1), r;
	} catch (r) {
		if (r instanceof Error && r.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw r;
		return r !== ne && console.warn("Failed to hydrate: ", r), t.recover === !1 && Fe(), zr(n), oe(!1), Fi(e, t);
	} finally {
		oe(r), D(i);
	}
}
function Li(e, t) {
	return Ri(e, t);
}
function Ri(e, { target: t, anchor: n, props: r = {}, events: i, context: a, intro: o = !0, transformError: s, renderer: c }) {
	var l = void 0, u = dn(() => {
		var o = n ?? Xr(t, Pr());
		Mi(o, { pending: () => {} }, (t) => {
			We({});
			var n = k;
			if (a && (n.c = a), i && (r.$$events = i), T && ki(t, null), l = e(t, r) || Ke(), T && (U.nodes.end = E, E === null || Kr(E) !== 8 || ri(E) !== "]")) throw ie(), ne;
			Ge();
		}, s);
		var u = c ? null : Si(t);
		return () => {
			if (u?.(), o !== n) {
				var e = Yr(o);
				e && ei(e, o);
			}
		};
	});
	return zi.set(l, u), l;
}
var zi = /* @__PURE__ */ new WeakMap();
function Bi(e, t) {
	let n = zi.get(e);
	return n ? (zi.delete(e), n(t)) : Promise.resolve();
}
// node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Vi = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	#a = null;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t, this.#a = tt;
	}
	#o = (e) => {
		if (this.#e.has(e)) try {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) wn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (wn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), $r(Jr(r.fragment)), Zr(this.anchor, r.fragment), n = r.effect, n.f &= ~l);
			}
			this.#s(e);
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = Hr();
						En(r, t), Xr(t, Pr()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Sn(r, i, !1)) : i();
			}
		} finally {}
	};
	#s = (e) => {
		for (let t of this.#e.keys()) t !== e && t.linked || this.#e.delete(t);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = F, r = Br();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = Hr(), a = Pr();
				Xr(i, a);
				var o = z(() => t(a));
				o.f |= l, n.unskip_new_effect(o), this.#n.set(e, {
					effect: o,
					fragment: i
				});
			} else this.#t.set(e, z(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#o), n.ondiscard(this.#s);
		} else T && (this.anchor = E), this.#o(n);
	}
};
function Hi(e) {
	k === null && ke("onMount"), Ve && k.l !== null ? Ui(k).m.push(e) : sn(() => {
		let t = J(e);
		if (typeof t == "function") return t;
	});
}
function Ui(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/if.js
function Wi(e, t, n = !1) {
	var r;
	T && (r = E, se());
	var i = new Vi(e), a = n ? o : 0;
	function s(e, t) {
		if (T) {
			var n = ue(r);
			if (e !== parseInt(n.substring(1))) {
				var a = le();
				D(a), i.anchor = a, oe(!1), i.ensure(e, t), oe(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	gn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, s(n, t);
		}), e || s(-1, null);
	}, a);
}
// node_modules/svelte/src/internal/shared/attributes.js
var Gi = [..." 	\n\r\f\xA0\v﻿"];
function Ki(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Gi.includes(r[o - 1])) && (s === r.length || Gi.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
// node_modules/svelte/src/internal/client/dom/blocks/each.js
function qi(e, t) {
	return t;
}
function Ji(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		Sn(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Xi(e, me(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var c = r.length === 0 && n !== null && e.pending.size === 0;
		if (c) {
			var l = n, u = Yr(l);
			zr(u), Xr(u, l), e.items.clear();
		}
		Xi(e, t, !c);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Yi(e) {
	var t = /* @__PURE__ */ new Set();
	for (let n of e.pending.values()) for (let r of n) t.add(e.items.get(r).e);
	return t;
}
function Xi(e, t, n = !0) {
	for (var r = e.pending.size > 0 ? Yi(e) : void 0, i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= l, En(a, Hr()), a !== e.effect.last && (oa(e, a.prev, a.next), oa(e, e.effect.last, a), oa(e, a, null))) : B(t[i], n);
	}
}
function Zi(e, t) {
	if (e.outrogroups !== null) {
		for (let n of e.outrogroups) if (n.pending.has(t) || n.done.has(t)) return !0;
	}
	return !1;
}
var Qi = /* @__PURE__ */ new WeakMap(), $i = {};
function ea() {
	var e = Qi.get(tt ?? $i);
	if (e) return e;
	var t = Pr();
	return Qi.set(tt ?? $i, t), t;
}
function ta(e, t, n, r, i, a = null) {
	var o = e, s = /* @__PURE__ */ new Map();
	if (t & 4) {
		var c = e;
		o = T ? D(/* @__PURE__ */ Fr(c)) : Xr(c, Pr());
	}
	T && se();
	var u = null, d = /* @__PURE__ */ pt(() => {
		var e = n();
		return de(e) ? e : e == null ? [] : me(e);
	}), f = /* @__PURE__ */ new Map(), p = !0;
	function m(e) {
		if (!(_.effect.f & 16384)) {
			try {
				_.pending.delete(e);
				var n = q(d);
				_.fallback = u, ra(_, n, o, t, r), u !== null && (n.length === 0 ? u.f & 33554432 ? (u.f ^= l, aa(u, null, o)) : wn(u) : Sn(u, () => {
					u = null;
				}));
			} finally {}
			g();
		}
	}
	function h(e) {
		_.pending.delete(e), _.effect.f & 16384 || g();
	}
	function g() {
		for (var e, t = _.effect.last; t !== null;) {
			var n = t.prev;
			if (t.f & 32 && t !== u) {
				if (!(t.f & 33554432)) break;
				e ??= Yi(_), !e.has(t) && !Zi(_, t) && B(t);
			}
			t = n;
		}
	}
	var _ = {
		effect: gn(() => {
			var e = q(d), c = e.length;
			let g = !1;
			T && ue(o) === "[!" != (c === 0) && (o = le(), D(o), oe(!1), g = !0);
			for (var _ = /* @__PURE__ */ new Set(), v = F, y = Br(), b = 0; b < c; b += 1) {
				T && Kr(E) === 8 && ri(E) === "]" && (o = E, g = !0, oe(!1));
				var x = e[b], S = r(x, b), C = p ? null : s.get(S);
				C ? (C.v && wt(C.v, x), C.i && wt(C.i, b), y && v.unskip_effect(C.e)) : (C = ia(s, p ? o : ea(), x, S, b, i, t, n), p || (C.e.f |= l, y && v.unskip_new_effect(C.e)), s.set(S, C)), _.add(S);
			}
			if (c === 0 && a && !u && (p ? u = z(() => a(o)) : (u = z(() => a(ea())), u.f |= l, y && v.unskip_new_effect(u))), y && u !== null && (c === 0 ? v.unskip_effect(u) : v.skip_effect(u)), c > _.size && Ae("", "", ""), T && c > 0 && D(le()), !p) {
				if (f.set(v, _), y) {
					for (let [e, t] of s) _.has(e) || v.skip_effect(t.e);
					v.oncommit(m), v.ondiscard(h);
				} else m(v);
			}
			g && oe(!0), q(d);
		}),
		flags: t,
		items: s,
		pending: f,
		outrogroups: null,
		fallback: u
	};
	p = !1, T && (o = E);
}
function na(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function ra(e, t, n, r, i) {
	var a = !!(r & 8), o = t.length, s = e.items, c = na(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (wn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) {
			if (_.f ^= l, _ === c) aa(_, null, n);
			else {
				var y = d ? d.next : c;
				_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), oa(e, d, _), oa(e, _, y), aa(_, y, n), d = _, p = [], m = [], c = na(d.next);
				continue;
			}
		}
		if (_ !== c) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) aa(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					oa(e, S.prev, C.next), oa(e, d, S), oa(e, C, b), c = b, d = C, --v, p = [], m = [];
				} else u.delete(_), aa(_, c, n), oa(e, _.prev, _.next), oa(e, _, d === null ? e.effect.first : d.next), oa(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; c !== null && c !== _;) (u ??= /* @__PURE__ */ new Set()).add(c), m.push(c), c = na(c.next);
			if (c === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, c = na(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Xi(e, me(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (c !== null || u !== void 0) {
		var ee = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || ee.push(_);
		for (; c !== null;) !(c.f & 8192) && c !== e.fallback && ee.push(c), c = na(c.next);
		var te = ee.length;
		if (te > 0) {
			var ne = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < te; v += 1) ee[v].nodes?.a?.measure();
				for (v = 0; v < te; v += 1) ee[v].nodes?.a?.fix();
			}
			Ji(e, ee, ne);
		}
	}
	a && Xe(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function ia(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? St(n) : /* @__PURE__ */ M(n, !1, !1) : null, l = o & 2 ? St(i) : null;
	return {
		v: c,
		i: l,
		e: z(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function aa(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ Ir(r);
		if (Zr(a, r), r === i) return;
		r = o;
	}
}
function oa(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
// node_modules/svelte/src/internal/client/dom/css.js
function sa(e, t) {
	fn(() => {
		e = U?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = Vr("style");
			e.id = t.hash, ti(e, t.code), Xr(r, e);
		}
	});
}
// node_modules/svelte/src/internal/client/dom/elements/class.js
function ca(e, t, n, r, i, a) {
	var o = e[b];
	if (T || o !== n || o === void 0) {
		var s = Ki(n, r, a);
		T && s === ai(e, "class") || (s == null ? oi(e, "class") : t ? e.className = s : Ur(e, "class", s)), e[b] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && pi(e, c, l);
	}
	return a;
}
// node_modules/svelte/src/internal/client/dom/elements/attributes.js
var la = Symbol("is custom element"), ua = Symbol("is html"), da = te ? "link" : "LINK", fa = te ? "progress" : "PROGRESS";
function pa(e) {
	if (T) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, si(e, "value")) {
					var n = e.value;
					ha(e, "value", null), e.value = n;
				}
				if (si(e, "checked")) {
					var r = e.checked;
					ha(e, "checked", null), e.checked = r;
				}
			}
		};
		e[C] = n, Xe(n), kn();
	}
}
function ma(e, t) {
	var n = ga(e);
	n.value !== (n.value = t ?? void 0) && (tt != null || e.value !== t || t === 0 && qr(e) === fa) && ii(e, t);
}
function ha(e, t, n, r) {
	var i = ga(e);
	if (!(T && (i[t] = ai(e, t), t === "src" || t === "srcset" || t === "href" && qr(e) === da))) {
		var a = i[t];
		a !== (i[t] = n) && (t === "loading" && (e[v] = n), n == null ? oi(e, t) : typeof n != "string" && va(e).has(t) ? e[t] = n : (!T || typeof n != "number" && typeof n != "boolean" || a !== String(n)) && Ur(e, t, n));
	}
}
function ga(e) {
	return e[y] ??= {
		[la]: qr(e).includes("-"),
		[ua]: tt == null && e.namespaceURI === "http://www.w3.org/1999/xhtml"
	};
}
var _a = /* @__PURE__ */ new Map();
function va(e) {
	var t = ai(e, "is") || qr(e), n = _a.get(t);
	if (n) return n;
	_a.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = ve(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.add(o);
		i = xe(i);
	}
	return n;
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function ya(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	jn(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = ba(e) ? xa(a) : a, n(a), F !== null && r.add(F), await xr(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (T && e.defaultValue !== e.value || J(t) == null && e.value) && (n(ba(e) ? xa(e.value) : e.value), F !== null && r.add(F)), mn(() => {
		var n = t();
		e === document.activeElement && r.has(R) || ba(e) && n === xa(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function ba(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function xa(e) {
	return e === "" ? null : +e;
}
// node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function Sa(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
// node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function Ca(e = !1) {
	let t = k, n = t.l.u;
	if (!n) return;
	let r = () => Er(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ lt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => q(i);
	}
	n.b.length && ln(() => {
		wa(t, r), Te(n.b);
	}), sn(() => {
		let e = J(() => n.m.map(we));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && sn(() => {
		wa(t, r), Te(n.a);
	});
}
function wa(e, t) {
	if (e.l.s) for (let t of e.l.s) q(t);
	t();
}
// node_modules/svelte/src/internal/client/dom/legacy/misc.js
function Ta(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of de(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
// node_modules/svelte/src/internal/client/reactivity/store.js
var Ea = !1;
function Da(e) {
	var t = Ea;
	try {
		return Ea = !1, [e(), Ea];
	} finally {
		Ea = t;
	}
}
// node_modules/svelte/src/internal/client/reactivity/props.js
function Oa(e, t, n, r) {
	var i = !Ve || !!(n & 2), a = !!(n & 8), o = !!(n & 16), s = r, c = !0, l = void 0, u = () => o && i ? (l ??= /* @__PURE__ */ lt(r), q(l)) : (c && (c = !1, s = o ? J(r) : r), s);
	let d;
	if (a) {
		var f = h in e || _ in e;
		d = _e(e, t)?.set ?? (f && t in e ? (n) => e[t] = n : void 0);
	}
	var p, m = !1;
	a ? [p, m] = Da(() => e[t]) : p = e[t], p === void 0 && r !== void 0 && (p = u(), d && (i && Ie(t), d(p)));
	var g = i ? () => {
		var n = e[t];
		return n === void 0 ? u() : (c = !0, n);
	} : () => {
		var n = e[t];
		return n !== void 0 && (s = void 0), n === void 0 ? s : n;
	};
	if (i && !(n & 4)) return g;
	if (d) {
		var v = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!i || !t || v || m) && d(t ? g() : e), e) : g();
		});
	}
	var y = !1, b = (n & 1 ? lt : pt)(() => (y = !1, g()));
	a && q(b);
	var x = U;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? q(b) : i && a ? Or(e) : e;
			return N(b, n), y = !0, s !== void 0 && (s = n), e;
		}
		return Mn && y || x.f & 16384 ? b.v : q(b);
	});
}
// node_modules/svelte/src/legacy/legacy-client.js
function ka(e) {
	return new Aa(e);
}
var Aa = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ M(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return q(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === _ || (q(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return N(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		}), i = {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		};
		this.#t = e.hydrate ? Ii(e.component, i) : Fi(e.component, i), e?.props?.$$host && e.sync !== !1 || Gt(), this.#e = r.$$events;
		for (let e of Object.keys(this.#t)) e !== "$set" && e !== "$destroy" && e !== "$on" && ge(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(r, e);
		}, this.#t.$destroy = () => {
			Bi(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, ja;
typeof HTMLElement == "function" && (ja = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = Vr("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = Na(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Ma(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = ka({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = un(() => {
				mn(() => {
					this.$$r = !0;
					for (let e of he(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Ma(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Ma(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return he(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function Ma(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function Na(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function Pa(e, t, n, r, i, a) {
	let o = class extends ja {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return he(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return he(t).forEach((e) => {
		ge(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = Ma(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (_e(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		ge(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
// MusicBrainzCard.svelte
var Fa = /* @__PURE__ */ Q("<div class=\"loading-state svelte-1ghyjz5\">Loading...</div>"), Ia = /* @__PURE__ */ Q("<div class=\"redirect-copy-group svelte-1ghyjz5\"><input type=\"text\" class=\"input-field readonly svelte-1ghyjz5\" readonly=\"\"/> <button class=\"btn-primary svelte-1ghyjz5\">Copy</button></div>"), La = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-1ghyjz5\">+ Add Account</button>"), Ra = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-1ghyjz5\">✓ Authenticated</span>"), za = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-1ghyjz5\">⚠ Not Authenticated</span>"), Ba = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-1ghyjz5\">● Active</span>"), Va = /* @__PURE__ */ Q("<div class=\"account-item svelte-1ghyjz5\"><div class=\"account-info svelte-1ghyjz5\"><div class=\"account-name svelte-1ghyjz5\"> </div> <div class=\"account-badges svelte-1ghyjz5\"><!> <!></div></div> <div class=\"account-actions svelte-1ghyjz5\"><button class=\"link-btn svelte-1ghyjz5\"> </button> <button> </button> <button class=\"btn-danger svelte-1ghyjz5\">✕</button></div></div>"), Ha = /* @__PURE__ */ Q("<div class=\"empty-accounts svelte-1ghyjz5\">No accounts linked.</div>"), Ua = /* @__PURE__ */ Q("<div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Server Configuration</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">API Base URL</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"https://musicbrainz.org/ws/2\"/> <p class=\"helper-text svelte-1ghyjz5\">Point this to a local MusicBrainz container for offline use.</p></label> <button class=\"btn-primary svelte-1ghyjz5\">Save Settings</button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">OAuth Credentials</h3> <div class=\"form-grid svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client ID</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"Enter Client ID\"/></label> <label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Client Secret</span> <div class=\"password-wrapper svelte-1ghyjz5\"><input class=\"input-field svelte-1ghyjz5\"/> <button class=\"toggle-visibility svelte-1ghyjz5\"> </button></div></label> <button class=\"btn-primary svelte-1ghyjz5\"> </button></div></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\">Redirect URI</h3> <button class=\"btn-ghost svelte-1ghyjz5\"> </button></div> <!></div> <div class=\"settings-section svelte-1ghyjz5\"><div class=\"section-header svelte-1ghyjz5\"><h3 class=\"section-title svelte-1ghyjz5\"> </h3> <!></div> <div class=\"accounts-list svelte-1ghyjz5\"></div></div>", 1), Wa = /* @__PURE__ */ Q("<div class=\"modal-overlay svelte-1ghyjz5\"><div class=\"modal-content svelte-1ghyjz5\"><div class=\"modal-header svelte-1ghyjz5\"><h3 class=\"modal-title svelte-1ghyjz5\">Add MusicBrainz Account</h3> <button class=\"close-btn svelte-1ghyjz5\">✕</button></div> <div class=\"modal-body svelte-1ghyjz5\"><label class=\"form-field svelte-1ghyjz5\"><span class=\"field-label svelte-1ghyjz5\">Display Name</span> <input type=\"text\" class=\"input-field svelte-1ghyjz5\" placeholder=\"My Account\"/></label></div> <div class=\"modal-footer svelte-1ghyjz5\"><button class=\"btn-ghost svelte-1ghyjz5\">Cancel</button> <button class=\"btn-primary svelte-1ghyjz5\">Add</button></div></div></div>"), Ga = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-1ghyjz5\"><div class=\"card-header svelte-1ghyjz5\"><div class=\"header-left svelte-1ghyjz5\"><h2 class=\"card-title svelte-1ghyjz5\">MusicBrainz</h2> <span class=\"type-badge svelte-1ghyjz5\">Metadata Provider</span></div></div> <!></section> <!>", 1), Ka = {
	hash: "svelte-1ghyjz5",
	code: ".plugin-card.svelte-1ghyjz5 {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle, #1e293b);}.header-left.svelte-1ghyjz5 {display:flex;align-items:center;gap:12px;}.card-title.svelte-1ghyjz5 {margin:0;font-size:20px;font-weight:700;}.type-badge.svelte-1ghyjz5 {font-size:11px;padding:4px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-1ghyjz5 {padding:24px;text-align:center;color:var(--text-secondary, #cbd5e1);}.settings-section.svelte-1ghyjz5 {margin-bottom:24px;}.section-header.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;}.section-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:600;}.form-grid.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:16px;}.form-field.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.field-label.svelte-1ghyjz5 {font-size:13px;font-weight:500;color:var(--text-secondary, #cbd5e1);}.input-field.svelte-1ghyjz5 {width:100%;padding:10px 14px;background:var(--bg-surface-elevated, #1e293b);border:1px solid var(--border-subtle, #334155);border-radius:8px;color:var(--text-primary, #f8fafc);font-size:14px;transition:all 0.2s;}.input-field.svelte-1ghyjz5:focus {outline:none;border-color:var(--color-primary, #14b8a6);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.input-field.readonly.svelte-1ghyjz5 {opacity:0.6;cursor:not-allowed;}.btn-primary.svelte-1ghyjz5 {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-1ghyjz5:hover:not(:disabled) {opacity:0.9;}.btn-primary.svelte-1ghyjz5:disabled {opacity:0.5;cursor:not-allowed;}.btn-ghost.svelte-1ghyjz5 {padding:8px 16px;background:rgba(255, 255, 255, 0.05);border:1px solid rgba(255, 255, 255, 0.1);color:var(--text-primary, #f8fafc);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.svelte-1ghyjz5:hover {background:rgba(255, 255, 255, 0.1);}.btn-ghost.active.svelte-1ghyjz5 {border-color:var(--color-primary, #14b8a6);color:var(--color-primary, #14b8a6);}.btn-danger.svelte-1ghyjz5 {background:rgba(239, 68, 68, 0.15);color:#ef4444;border:none;padding:8px 12px;border-radius:6px;cursor:pointer;}.helper-text.svelte-1ghyjz5 {font-size:11px;color:var(--text-secondary, #cbd5e1);margin-top:4px;}.redirect-copy-group.svelte-1ghyjz5 {display:flex;gap:8px;align-items:stretch;}.redirect-copy-group.svelte-1ghyjz5 .input-field:where(.svelte-1ghyjz5) {flex:1;font-family:monospace;}.accounts-list.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:8px;}.account-item.svelte-1ghyjz5 {display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid rgba(255, 255, 255, 0.05);border-radius:8px;}.account-info.svelte-1ghyjz5 {display:flex;flex-direction:column;gap:4px;}.account-name.svelte-1ghyjz5 {font-weight:600;font-size:14px;}.account-badges.svelte-1ghyjz5 {display:flex;gap:8px;}.status-badge.svelte-1ghyjz5 {font-size:10px;padding:2px 6px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-1ghyjz5 {background:rgba(34, 197, 94, 0.15);color:#22c55e;}.status-badge.warning.svelte-1ghyjz5 {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-1ghyjz5 {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.account-actions.svelte-1ghyjz5 {display:flex;gap:12px;align-items:center;}.link-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--color-primary, #14b8a6);font-size:13px;font-weight:600;cursor:pointer;}.link-btn.svelte-1ghyjz5:hover {text-decoration:underline;}.password-wrapper.svelte-1ghyjz5 {position:relative;display:flex;align-items:center;width:100%;}.toggle-visibility.svelte-1ghyjz5 {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary, #f8fafc);}.modal-overlay.svelte-1ghyjz5 {position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000;backdrop-filter:blur(4px);}.modal-content.svelte-1ghyjz5 {background:#0f1216;border:1px solid var(--border-subtle, #1e293b);border-radius:12px;width:100%;max-width:440px;box-shadow:0 24px 48px rgba(0,0,0,0.5);}.modal-header.svelte-1ghyjz5 {padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;align-items:center;}.modal-title.svelte-1ghyjz5 {margin:0;font-size:16px;font-weight:700;}.close-btn.svelte-1ghyjz5 {background:none;border:none;color:var(--text-secondary, #cbd5e1);font-size:20px;cursor:pointer;}.modal-body.svelte-1ghyjz5 {padding:20px;display:flex;flex-direction:column;gap:16px;}.modal-footer.svelte-1ghyjz5 {padding:16px 20px;border-top:1px solid rgba(255,255,255,0.05);display:flex;justify-content:flex-end;gap:12px;}.empty-accounts.svelte-1ghyjz5 {text-align:center;padding:16px;color:var(--text-secondary, #cbd5e1);font-size:13px;background:rgba(255, 255, 255, 0.02);border-radius:8px;border:1px dashed rgba(255, 255, 255, 0.1);}"
};
function qa(e, t) {
	We(t, !1), sa(e, Ka);
	let n = Oa(t, "apiBase", 12, ""), r = /* @__PURE__ */ M(!0), i = /* @__PURE__ */ M([]), a = /* @__PURE__ */ M(""), o = /* @__PURE__ */ M(""), s = /* @__PURE__ */ M(""), c = /* @__PURE__ */ M(""), l = !1, u = !1, d = /* @__PURE__ */ M(!1), f = /* @__PURE__ */ M(!1), p = /* @__PURE__ */ M(!1), m = /* @__PURE__ */ M("https://musicbrainz.org/ws/2"), h = /* @__PURE__ */ M(!1), g = /* @__PURE__ */ M(""), _ = /* @__PURE__ */ M(!1);
	Hi(async () => {
		await v(), N(r, !1);
	});
	async function v() {
		try {
			let e = await (await fetch(`${n()}/accounts`)).json();
			e && (N(i, e.accounts || []), N(a, e.redirect_uri || ""), l = e.client_id_configured || !1, u = e.client_secret_configured || !1, N(p, !!q(a)));
			let t = await (await fetch(`${n()}/settings`)).json();
			t?.settings && N(m, t.settings.api_base_url || "https://musicbrainz.org/ws/2");
			let r = await (await fetch(`${n()}/credentials`)).json();
			r?.credentials && (N(o, r.credentials.client_id || ""), N(c, u ? "••••••••" : ""));
		} catch (e) {
			console.error("Failed to load MusicBrainz data:", e);
		}
	}
	async function y() {
		if (!q(o).trim()) {
			console.error("Client ID is required");
			return;
		}
		let e = { client_id: q(o) };
		if (q(s).trim()) e.client_secret = q(s);
		else if (!u) {
			console.error("Client Secret is required");
			return;
		}
		try {
			N(f, !0), await fetch(`${n()}/credentials`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ credentials: e })
			}), N(s, ""), await v();
		} catch (e) {
			console.error("Failed to save credentials:", e);
		} finally {
			N(f, !1);
		}
	}
	async function b() {
		try {
			await fetch(`${n()}/settings`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ settings: { api_base_url: q(m) } })
			}), console.log("MusicBrainz settings saved");
		} catch (e) {
			console.error("Failed to save settings:", e);
		}
	}
	function x() {
		N(g, ""), N(h, !0);
	}
	function S() {
		N(h, !1), N(g, "");
	}
	async function C() {
		let e = q(g).trim();
		if (e) try {
			N(_, !0), await fetch(`${n()}/accounts`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ account_name: e })
			}), S(), await v();
		} catch (e) {
			console.error("Failed to add account:", e);
		} finally {
			N(_, !1);
		}
	}
	async function ee(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			await fetch(`${n()}/accounts/${e}`, { method: "DELETE" }), await v();
		} catch (e) {
			console.error("Failed to delete account:", e);
		}
	}
	async function te(e, t) {
		try {
			await fetch(`${n()}/accounts/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), await v();
		} catch (e) {
			console.error("Failed to update account status:", e);
		}
	}
	async function ne(e) {
		if (!l || !u) alert("Save your Client ID and Secret first.");
		else try {
			let t = (await (await fetch(`${n()}/auth?account_id=${e}`)).json())?.auth_url;
			t && (window.open(t, "_blank", "noopener,noreferrer"), setTimeout(() => v(), 5e3));
		} catch (e) {
			console.error("Failed to start OAuth:", e);
		}
	}
	var w = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Gt();
		}
	};
	Ca();
	var re = Ga(), ie = Lr(re), ae = X(Y(ie), 2), T = (e) => {
		$(e, Fa());
	}, oe = (e) => {
		var t = Ua(), n = Lr(t), r = X(Y(n), 2), l = Y(r), u = X(Y(l), 2);
		pa(u), ce(2), O(l);
		var h = X(l, 2);
		O(r), O(n);
		var g = X(n, 2), _ = X(Y(g), 2), v = Y(_), S = X(Y(v), 2);
		pa(S), O(v);
		var C = X(v, 2), w = X(Y(C), 2), re = Y(w);
		pa(re);
		var ie = X(re, 2), ae = Rr(ie, !0);
		O(w), O(C);
		var T = X(C, 2), oe = Rr(T, !0);
		O(_), O(g);
		var E = X(g, 2), D = Y(E), se = X(Y(D), 2), le = Rr(se, !0);
		O(D);
		var ue = X(D, 2), de = (e) => {
			var t = Ia(), n = Y(t);
			pa(n);
			var r = X(n, 2);
			O(t), hn(() => ma(n, q(a))), Z("click", r, () => {
				navigator.clipboard.writeText(q(a)), alert("Copied!");
			}), $(e, t);
		};
		Wi(ue, (e) => {
			q(p) || e(de);
		}), O(E);
		var fe = X(E, 2), pe = Y(fe), me = Y(pe), he = Rr(me), ge = X(me, 2), _e = (e) => {
			var t = La();
			Z("click", t, x), $(e, t);
		};
		Wi(ge, (e) => {
			q(i), J(() => q(i).length < 10) && e(_e);
		}), O(pe);
		var ve = X(pe, 2);
		ta(ve, 5, () => q(i), qi, (e, t) => {
			var n = Va(), r = Y(n), i = Y(r), a = Rr(i, !0), o = X(i, 2), s = Y(o), c = (e) => {
				$(e, Ra());
			}, l = (e) => {
				$(e, za());
			};
			Wi(s, (e) => {
				q(t), J(() => q(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = X(s, 2), d = (e) => {
				$(e, Ba());
			};
			Wi(u, (e) => {
				q(t), J(() => q(t).is_active) && e(d);
			}), O(o), O(r);
			var f = X(r, 2), p = Y(f), m = Rr(p, !0), h = X(p, 2);
			let g;
			var _ = Rr(h, !0), v = X(h, 2);
			O(f), O(n), hn(() => {
				Pi(a, (q(t), J(() => q(t).display_name || q(t).account_name))), Pi(m, (q(t), J(() => q(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), g = ca(h, 1, "btn-ghost svelte-1ghyjz5", null, g, { active: q(t).is_active }), Pi(_, (q(t), J(() => q(t).is_active ? "Deactivate" : "Activate")));
			}), Z("click", p, () => ne(q(t).id)), Z("click", h, () => te(q(t).id, q(t).is_active)), Z("click", v, () => ee(q(t).id, q(t).display_name || q(t).account_name)), $(e, n);
		}, (e) => {
			$(e, Ha());
		}), O(ve), O(fe), hn(() => {
			ha(re, "type", q(d) ? "text" : "password"), ha(re, "placeholder", q(c) || "Enter Client Secret"), Pi(ae, q(d) ? "🙈" : "👁️"), T.disabled = q(f), Pi(oe, q(f) ? "Saving..." : "Save Credentials"), Pi(le, q(p) ? "Expand" : "Collapse"), Pi(he, `Accounts (${q(i), J(() => q(i).length) ?? ""}/10)`);
		}), ya(u, () => q(m), (e) => N(m, e)), Z("click", h, b), ya(S, () => q(o), (e) => N(o, e)), ya(re, () => q(s), (e) => N(s, e)), Z("click", ie, () => N(d, !q(d))), Z("click", T, y), Z("click", se, () => N(p, !q(p))), $(e, t);
	};
	Wi(ae, (e) => {
		q(r) ? e(T) : e(oe, -1);
	}), O(ie);
	var E = X(ie, 2), D = (e) => {
		var n = Wa(), r = Y(n), i = Y(r), a = X(Y(i), 2);
		O(i);
		var o = X(i, 2), s = Y(o), c = X(Y(s), 2);
		pa(c), O(s), O(o);
		var l = X(o, 2), u = Y(l), d = X(u, 2);
		O(l), O(r), O(n), hn(() => d.disabled = q(_)), Z("click", a, S), ya(c, () => q(g), (e) => N(g, e)), Z("click", u, S), Z("click", d, C), Z("click", r, Sa(function(e) {
			Ta.call(this, t, e);
		})), Z("click", n, S), $(e, n);
	};
	return Wi(E, (e) => {
		q(h) && e(D);
	}), $(e, re), Ge(w);
}
customElements.define("musicbrainz-dashboard-card", Pa(qa, { apiBase: {} }, [], [], { mode: "open" }));
// MusicBrainzSettingsCard.svelte
var Ja = /* @__PURE__ */ Q("<div class=\"loading-state svelte-18cwlk6\">Loading configuration…</div>"), Ya = /* @__PURE__ */ Q("<span class=\"status-tag success svelte-18cwlk6\">● Configured</span>"), Xa = /* @__PURE__ */ Q("<div class=\"warning-box svelte-18cwlk6\">⚠ A User Token is required to enable contributions. Please enter your token above.</div>"), Za = /* @__PURE__ */ Q("<div class=\"feedback error svelte-18cwlk6\"> </div>"), Qa = /* @__PURE__ */ Q("<div class=\"feedback success svelte-18cwlk6\">✓ Configuration saved successfully.</div>"), $a = /* @__PURE__ */ Q("<div class=\"info-banner svelte-18cwlk6\"><p>MusicBrainz works out-of-the-box for metadata retrieval. An account is only needed for contributing data back to the community.</p></div> <div class=\"form-section svelte-18cwlk6\"><label class=\"field-label svelte-18cwlk6\" for=\"mb-user-token\">User Token / API Key <!></label> <p class=\"helper-text svelte-18cwlk6\">Obtain your personal access token from <a href=\"https://musicbrainz.org/account/applications\" target=\"_blank\" rel=\"noopener noreferrer\" class=\"link svelte-18cwlk6\">musicbrainz.org/account/applications</a>.\n        Required for submitting ISRC codes and metadata corrections.</p> <div class=\"input-wrapper svelte-18cwlk6\"><input id=\"mb-user-token\" class=\"input-field svelte-18cwlk6\"/> <button type=\"button\" class=\"toggle-btn svelte-18cwlk6\"> </button></div></div> <div class=\"toggle-card svelte-18cwlk6\"><div class=\"toggle-header svelte-18cwlk6\"><p class=\"toggle-label svelte-18cwlk6\">Auto-Contribute Missing Data</p> <button type=\"button\" role=\"switch\" aria-label=\"Toggle auto-contribute\"><span class=\"switch-thumb svelte-18cwlk6\"></span></button></div> <p class=\"helper-text mt-2 svelte-18cwlk6\">When enabled, EchoSync will automatically submit missing acoustic fingerprints (AcoustID) and \n        ISRC data back to MusicBrainz during imports.</p> <!></div> <!> <!> <div class=\"actions svelte-18cwlk6\"><button class=\"btn-primary svelte-18cwlk6\"> </button></div>", 1), eo = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-18cwlk6\"><div class=\"card-header svelte-18cwlk6\"><svg width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" class=\"accent-icon svelte-18cwlk6\"><circle cx=\"12\" cy=\"12\" r=\"10\"></circle><path d=\"M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3\"></path><line x1=\"12\" y1=\"17\" x2=\"12.01\" y2=\"17\"></line></svg> <div><h2 class=\"card-title svelte-18cwlk6\">MusicBrainz Configuration</h2> <p class=\"card-subtitle svelte-18cwlk6\">Global music encyclopedia & metadata source</p></div> <span class=\"type-badge svelte-18cwlk6\">Metadata</span></div> <!></section>"), to = {
	hash: "svelte-18cwlk6",
	code: ".plugin-card.svelte-18cwlk6 {background:var(--bg-surface);backdrop-filter:blur(12px);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);padding:24px;margin-bottom:16px;color:var(--text-primary);}.card-header.svelte-18cwlk6 {display:flex;align-items:center;gap:12px;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid var(--border-subtle);}.accent-icon.svelte-18cwlk6 {color:var(--color-primary);}.card-title.svelte-18cwlk6 {margin:0;font-size:1.25rem;font-weight:600;line-height:1.2;}.card-subtitle.svelte-18cwlk6 {margin:4px 0 0;font-size:0.75rem;color:var(--text-muted);}.type-badge.svelte-18cwlk6 {margin-left:auto;font-size:11px;padding:4px 8px;background:rgba(16, 185, 129, 0.1);color:#10b981;border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-18cwlk6 {padding:20px;text-align:center;color:var(--text-muted);}.info-banner.svelte-18cwlk6 {margin-bottom:24px;padding:12px 16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:8px;font-size:0.8125rem;color:var(--text-muted);line-height:1.4;}.form-section.svelte-18cwlk6 {margin-bottom:24px;}.field-label.svelte-18cwlk6 {display:block;font-size:0.875rem;font-weight:500;margin-bottom:4px;}.status-tag.success.svelte-18cwlk6 {margin-left:8px;font-size:11px;padding:2px 6px;background:rgba(16, 185, 129, 0.15);color:#10b981;border-radius:4px;}.helper-text.svelte-18cwlk6 {font-size:0.75rem;color:var(--text-muted);margin-bottom:8px;line-height:1.5;}.link.svelte-18cwlk6 {color:var(--color-primary);text-decoration:none;}.link.svelte-18cwlk6:hover {text-decoration:underline;}.input-wrapper.svelte-18cwlk6 {position:relative;display:flex;align-items:center;}.input-field.svelte-18cwlk6 {width:100%;padding:10px 14px;padding-right:40px;background:rgba(0, 0, 0, 0.2);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);color:var(--text-primary);font-size:0.875rem;transition:border-color 0.2s;}.input-field.svelte-18cwlk6:focus {outline:none;border-color:var(--color-primary);}.toggle-btn.svelte-18cwlk6 {position:absolute;right:12px;background:transparent;border:none;cursor:pointer;font-size:1.1rem;opacity:0.6;transition:opacity 0.2s;}.toggle-btn.svelte-18cwlk6:hover {opacity:1;}.toggle-card.svelte-18cwlk6 {margin-bottom:24px;padding:16px;background:rgba(255, 255, 255, 0.03);border:1px solid var(--border-subtle);border-radius:var(--radius, 12px);}.toggle-header.svelte-18cwlk6 {display:flex;justify-content:space-between;align-items:center;}.toggle-label.svelte-18cwlk6 {margin:0;font-size:0.875rem;font-weight:600;}.switch.svelte-18cwlk6 {position:relative;width:44px;height:24px;background:rgba(255, 255, 255, 0.2);border-radius:999px;border:none;cursor:pointer;transition:background 0.2s;}.switch.active.svelte-18cwlk6 {background:var(--color-primary, #14b8a6);}.switch-thumb.svelte-18cwlk6 {position:absolute;top:2px;left:2px;width:20px;height:20px;background:white;border-radius:50%;transition:transform 0.2s;}.switch.active.svelte-18cwlk6 .switch-thumb:where(.svelte-18cwlk6) {transform:translateX(20px);}.warning-box.svelte-18cwlk6 {margin-top:12px;padding:8px 12px;background:rgba(245, 158, 11, 0.1);border:1px solid rgba(245, 158, 11, 0.2);border-radius:6px;font-size:11px;color:#fbbf24;line-height:1.4;}.feedback.svelte-18cwlk6 {margin-bottom:16px;padding:10px 14px;border-radius:var(--radius, 12px);font-size:0.875rem;}.feedback.error.svelte-18cwlk6 {background:rgba(239, 68, 68, 0.1);border:1px solid #ef4444;color:#ef4444;}.feedback.success.svelte-18cwlk6 {background:rgba(16, 185, 129, 0.1);border:1px solid #10b981;color:#10b981;}.actions.svelte-18cwlk6 {display:flex;justify-content:flex-end;}.btn-primary.svelte-18cwlk6 {padding:10px 24px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);font-weight:600;border:none;border-radius:var(--radius, 12px);cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-18cwlk6:hover:not(:disabled) {opacity:0.9;box-shadow:0 4px 12px rgba(20, 184, 166, 0.2);}.btn-primary.svelte-18cwlk6:active:not(:disabled) {transform:scale(0.98);}.btn-primary.svelte-18cwlk6:disabled {opacity:0.5;cursor:not-allowed;}.mt-2.svelte-18cwlk6 {margin-top:8px;}"
};
function no(e, t) {
	We(t, !1), sa(e, to);
	let n = Oa(t, "apiBase", 12, ""), r = /* @__PURE__ */ M(!0), i = /* @__PURE__ */ M(!1), a = /* @__PURE__ */ M(!1), o = /* @__PURE__ */ M(""), s = /* @__PURE__ */ M(""), c = /* @__PURE__ */ M(!1), l = /* @__PURE__ */ M(!1), u = /* @__PURE__ */ M(!1);
	Hi(async () => {
		await d(), N(r, !1);
	});
	async function d() {
		try {
			n();
			let e = await fetch(`${n()}/config`);
			if (e.ok) {
				let t = await e.json();
				N(c, t.token_configured ?? !1), N(u, t.auto_contribute ?? !1), q(c) && N(s, "");
			}
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Failed to load config:", e);
		}
	}
	async function f() {
		let e = { auto_contribute: q(u) };
		if (q(s).trim()) e.user_token = q(s).trim();
		else if (q(u) && !q(c)) {
			N(o, "A User Token is required to enable auto-contributions.");
			return;
		}
		N(o, ""), N(i, !0), N(a, !1);
		try {
			n();
			let t = await fetch(`${n()}/config`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			});
			if (t.ok) {
				let e = await t.json();
				N(c, e.token_configured ?? q(c)), N(s, ""), N(a, !0), dispatchEvent(new CustomEvent("musicbrainz-config-saved", {
					bubbles: !0,
					composed: !0,
					detail: {
						auto_contribute: q(u),
						token_configured: q(c)
					}
				})), setTimeout(() => N(a, !1), 3e3);
			} else {
				let e = await t.json().catch(() => ({}));
				N(o, e.error || "Failed to save configuration.");
			}
		} catch (e) {
			console.error("[MusicBrainzSettingsCard] Save error:", e), N(o, "Network error while saving. Please try again.");
		} finally {
			N(i, !1);
		}
	}
	var p = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Gt();
		}
	};
	Ca();
	var m = eo(), h = X(Y(m), 2), g = (e) => {
		$(e, Ja());
	}, _ = (e) => {
		var t = $a(), n = X(Lr(t), 2), r = Y(n), d = X(Y(r)), p = (e) => {
			$(e, Ya());
		};
		Wi(d, (e) => {
			q(c) && e(p);
		}), O(r);
		var m = X(r, 4), h = Y(m);
		pa(h);
		var g = X(h, 2), _ = Rr(g, !0);
		O(m), O(n);
		var v = X(n, 2), y = Y(v), b = X(Y(y), 2);
		O(y);
		var x = X(y, 4), S = (e) => {
			$(e, Xa());
		};
		Wi(x, (e) => {
			q(u) && !q(c) && !q(s) && e(S);
		}), O(v);
		var C = X(v, 2), ee = (e) => {
			var t = Za(), n = Rr(t);
			hn(() => Pi(n, `⚠ ${q(o) ?? ""}`)), $(e, t);
		};
		Wi(C, (e) => {
			q(o) && e(ee);
		});
		var te = X(C, 2), ne = (e) => {
			$(e, Qa());
		};
		Wi(te, (e) => {
			q(a) && e(ne);
		});
		var w = X(te, 2), re = Y(w), ie = Rr(re, !0);
		O(w), hn(() => {
			ha(h, "type", q(l) ? "text" : "password"), ha(h, "placeholder", q(c) ? "••••••••  (leave blank to keep current)" : "Enter your MusicBrainz user token"), ha(g, "title", q(l) ? "Hide token" : "Show token"), ha(g, "aria-label", q(l) ? "Hide token" : "Show token"), Pi(_, q(l) ? "🙈" : "👁️"), ha(b, "aria-checked", q(u)), ca(b, 1, `switch ${q(u) ? "active" : ""}`, "svelte-18cwlk6"), re.disabled = q(i), Pi(ie, q(i) ? "Saving…" : "Save Settings");
		}), ya(h, () => q(s), (e) => N(s, e)), Z("click", g, () => N(l, !q(l))), Z("click", b, () => N(u, !q(u))), Z("click", re, f), $(e, t);
	};
	return Wi(h, (e) => {
		q(r) ? e(g) : e(_, -1);
	}), O(m), $(e, m), Ge(p);
}
customElements.define("musicbrainz-settings-card", Pa(no, { apiBase: {} }, [], [], { mode: "open" }));
